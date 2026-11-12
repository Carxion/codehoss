"""basedpyright language server in a sandbox container, bridged to the browser.

The browser speaks LSP JSON messages over a WebSocket; this module adds/removes the
Content-Length framing used on stdio. The server runs from the module's own image,
so completions reflect exactly the packages learner code will run with. It gets its
own container (not the session's) so learner code can't starve or kill it.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import threading
import uuid
from collections.abc import Callable

from hoss.sandbox import LABEL, Limits, lockdown_flags

# Node needs more headroom than learner scripts do; analysing big libraries (pandas)
# needs more again, so a module's own memory setting raises this floor.
LSP_LIMITS = Limits(memory="512m", pids=64, workspace="16m")


class LanguageServer:
    def __init__(self, image: str, on_message: Callable[[dict], None], memory: str | None = None):
        self.name = f"hoss-lsp-{uuid.uuid4().hex[:12]}"
        cmd = [
            "docker", "run", "--rm", "-i",
            "--name", self.name,
            "--label", f"{LABEL}=lsp",
            *lockdown_flags(_limits(memory)),
            image,
            "basedpyright-langserver", "--stdio",
        ]  # fmt: skip
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        self._on_message = on_message
        self._write_lock = threading.Lock()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def send(self, message: dict) -> None:
        body = json.dumps(message).encode("utf-8")
        frame = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body
        assert self._proc.stdin
        with self._write_lock:
            try:
                self._proc.stdin.write(frame)
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                pass  # server has gone; close() will clean up

    def close(self) -> None:
        if self._proc.stdin:
            try:
                self._proc.stdin.close()  # EOF makes the server exit; --rm removes it
            except OSError:
                pass
        try:
            self._proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        subprocess.run(["docker", "rm", "--force", self.name], capture_output=True)

    @property
    def alive(self) -> bool:
        return self._proc.poll() is None

    def _read_loop(self) -> None:
        stdout = self._proc.stdout
        assert stdout
        while True:
            length = None
            while True:
                line = stdout.readline()
                if not line:
                    return  # server exited
                line = line.strip()
                if not line:
                    break
                name, _, value = line.decode("ascii", errors="replace").partition(":")
                if name.lower() == "content-length":
                    length = int(value.strip())
            if length is None:
                continue
            body = stdout.read(length)
            try:
                self._on_message(json.loads(body))
            except ValueError:
                continue


def _limits(memory: str | None) -> Limits:
    if memory is None or _megabytes(memory) <= _megabytes(LSP_LIMITS.memory):
        return LSP_LIMITS
    return dataclasses.replace(LSP_LIMITS, memory=memory)


def _megabytes(size: str) -> int:
    return int(size[:-1]) * (1024 if size.endswith("g") else 1)
