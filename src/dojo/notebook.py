"""Host side of notebook kernels (see dojo._kernel for the side in the sandbox).

A Kernel is one long-lived Python process inside the learner's session container.
Variables persist between cells until it is restarted. Each cell gets a wall-clock
limit: past it the kernel is interrupted, and if that doesn't work, restarted.
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


class Kernel:
    def __init__(self, container: str, on_message: OnMessage):
        self.container = container
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
        line = json.dumps({"id": exec_id, "code": code}) + "\n"
        assert self._proc.stdin
        try:
            self._proc.stdin.write(line.encode("utf-8"))
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            self._emit({"type": "dead", "reason": "The kernel stopped. Restart it to continue."})
        return exec_id

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
                running = dict(self._busy_since)
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
