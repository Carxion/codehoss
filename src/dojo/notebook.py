"""Host side of notebook kernels (see dojo._kernel for the side in the sandbox).

A Kernel is one long-lived Python process inside the learner's session container.
Variables persist between cells until it is restarted. Each cell gets a wall-clock
limit: past it the kernel is interrupted, and if that doesn't work, restarted.

Cells that call dojo_ai send "ai_request" messages; the kernel answers them through
`ai_handler` (the API binds it to the learner's chosen model). Time spent waiting for
a model doesn't count against the cell's limit.
"""

from __future__ import annotations

import itertools
import json
import re
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from dojo.explain import explain

KERNEL_SOURCE = (Path(__file__).parent / "_kernel.py").read_text(encoding="utf-8")
CELL_TIMEOUT_S = 60
INTERRUPT_GRACE_S = 5
CELL_LINE = re.compile(r"line (\d+)")

Message = dict
OnMessage = Callable[[Message], None]
# (kind, payload) -> result dict, e.g. {"text": ..., "provider": ..., "model": ...}.
# Raises an exception with a learner-friendly message when the model can't answer.
AIHandler = Callable[[str, dict], dict]


class Kernel:
    def __init__(self, container: str, on_message: OnMessage, ai_handler: AIHandler | None = None):
        self.container = container
        self._ai_handler = ai_handler
        self._ai_waiting: set[int] = set()
        self._write_lock = threading.Lock()
        self.workdir = f"/work/nb-{uuid.uuid4().hex[:12]}"
        self._on_message = on_message
        self._ids = itertools.count(1)
        self._pid: int | None = None
        self._ready = threading.Event()
        self._busy_since: dict[int, float] = {}
        self._codes: dict[int, str] = {}
        self._tags: dict[int, str] = {}
        self._lock = threading.Lock()
        self._closed = False
        script = 'mkdir -p "$1" && cd "$1" && exec python -u -c "$0"'
        self._proc = subprocess.Popen(
            ["docker", "exec", "-i", container, "sh", "-c", script, KERNEL_SOURCE, self.workdir],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        threading.Thread(target=self._read_loop, daemon=True).start()
        threading.Thread(target=self._watchdog, daemon=True).start()

    # --- control -------------------------------------------------------------------

    def execute(self, code: str, tag: str = "") -> int:
        """Queue a cell; returns its id. Results arrive through on_message, each carrying
        `tag` (the browser's cell id) so outputs land under the right cell."""
        exec_id = next(self._ids)
        with self._lock:
            self._codes[exec_id] = code
            self._tags[exec_id] = tag
            self._busy_since[exec_id] = time.monotonic()
        self._write({"id": exec_id, "code": code})
        return exec_id

    def _write(self, message: dict) -> None:
        assert self._proc.stdin
        line = (json.dumps(message) + "\n").encode("utf-8")
        try:
            with self._write_lock:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            self._emit({"type": "dead", "reason": "The kernel stopped. Restart it to continue."})

    def wait_ready(self, timeout: float = 30) -> bool:
        return self._ready.wait(timeout)

    def interrupt(self) -> None:
        if self._pid:
            self._signal("INT")

    def close(self) -> None:
        self._closed = True
        if self._proc.stdin:
            try:
                self._proc.stdin.close()
            except OSError:
                pass
        if self._pid:
            self._signal("KILL")
        self._proc.kill()
        subprocess.run(
            ["docker", "exec", self.container, "rm", "-rf", self.workdir],
            capture_output=True,
        )

    def _signal(self, name: str) -> None:
        # Through sh: slim images have no kill binary, only the shell builtin.
        subprocess.run(
            ["docker", "exec", self.container, "sh", "-c", f"kill -{name} {self._pid}"],
            capture_output=True,
        )

    @property
    def alive(self) -> bool:
        return self._proc.poll() is None

    # --- internals -----------------------------------------------------------------

    def _emit(self, message: Message) -> None:
        if not self._closed:
            self._on_message(message)

    def _read_loop(self) -> None:
        assert self._proc.stdout
        for raw in self._proc.stdout:
            try:
                message = json.loads(raw)
            except ValueError:
                continue
            kind = message.get("type")
            if kind == "ready":
                self._pid = message["pid"]
                self._ready.set()
                self._emit({"type": "status", "state": "idle"})
                continue
            if kind == "ai_request":
                threading.Thread(target=self._answer_ai, args=(message,), daemon=True).start()
                continue
            if kind == "error":
                message.update(self._explain(message))
            with self._lock:
                message["cell"] = self._tags.get(message.get("id"), "")
                if kind == "done":
                    self._busy_since.pop(message["id"], None)
                    self._codes.pop(message["id"], None)
                    self._tags.pop(message["id"], None)
            self._emit(message)
        self._emit(
            {"type": "dead", "reason": "The kernel stopped (it may have run out of memory)."}
        )

    def _answer_ai(self, request: Message) -> None:
        exec_id, started = request.get("id"), time.monotonic()
        with self._lock:
            self._ai_waiting.add(exec_id)
            cell = self._tags.get(exec_id, "")
        event = {"type": "ai", "cell": cell, "kind": request.get("kind")}
        try:
            if self._ai_handler is None:
                raise RuntimeError("AI isn't available here.")
            result = self._ai_handler(request["kind"], request.get("payload") or {})
            reply = {"ai_reply": request["req"], "ok": True, "result": result}
            event.update(ok=True, provider=result.get("provider"), model=result.get("model"))
        except Exception as e:  # noqa: BLE001 - every failure goes back to the learner
            reply = {"ai_reply": request["req"], "ok": False, "error": str(e)}
            event.update(ok=False, error=str(e))
        elapsed = time.monotonic() - started
        with self._lock:
            self._ai_waiting.discard(exec_id)
            # Waiting for the model doesn't count against the cell's time limit.
            if exec_id in self._busy_since:
                self._busy_since[exec_id] += elapsed
        event["ms"] = round(elapsed * 1000)
        self._write(reply)
        if request.get("kind") != "backend":  # backend() asks, it doesn't call a model
            self._emit(event)

    def _explain(self, error: Message) -> Message:
        with self._lock:
            code = self._codes.get(error.get("id"), "")
        _, message = explain(error["ename"], error["evalue"], code)
        line = CELL_LINE.search(error.get("traceback", ""))
        return {"explanation": message, "line": int(line[1]) if line else None}

    def _watchdog(self) -> None:
        interrupted: set[int] = set()
        while self.alive and not self._closed:
            time.sleep(1)
            now = time.monotonic()
            with self._lock:
                running = {k: v for k, v in self._busy_since.items() if k not in self._ai_waiting}
            for exec_id, started in running.items():
                if now - started > CELL_TIMEOUT_S and exec_id not in interrupted:
                    interrupted.add(exec_id)
                    self._emit(
                        {
                            "id": exec_id,
                            "cell": self._tags.get(exec_id, ""),
                            "type": "stream",
                            "name": "stderr",
                            "text": f"\n[Stopped: the cell ran for over {CELL_TIMEOUT_S}s]\n",
                        }
                    )
                    self.interrupt()
                elif now - started > CELL_TIMEOUT_S + INTERRUPT_GRACE_S:
                    self._emit(
                        {
                            "type": "dead",
                            "reason": "The cell would not stop, so the kernel was restarted.",
                        }
                    )
                    self.close()
                    return
