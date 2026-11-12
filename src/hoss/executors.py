"""Where learner code actually runs.

An executor takes a set of files plus a command, runs it, and hands back the
output and any files asked for. The grader doesn't care which one it gets:

- LocalExecutor: a temp folder on this machine (fast; tests and authoring only)
- DockerSession: a locked-down per-learner container (see hoss.sandbox)
"""

from __future__ import annotations

import codecs
import io
import os
import queue
import shlex
import subprocess
import sys
import tarfile
import tempfile
import threading
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

OutputCallback = Callable[[str], None]

# `timeout` (coreutils) exits 124 when it had to stop the command.
TIMEOUT_EXIT = 124
# A process killed for exceeding `ulimit -t` dies of SIGXCPU (24).
CPU_LIMIT_EXITS = {128 + 24, -24}
# Extra host-side allowance on top of the in-container timeout for `docker exec` overhead.
DOCKER_GRACE_S = 10.0


class StdinFeed:
    """Keyboard input that arrives while a program is running (interactive runs)."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str | None] = queue.Queue()

    def write(self, text: str) -> None:
        self._queue.put(text)

    def close(self) -> None:
        self._queue.put(None)

    def __iter__(self) -> Iterator[str]:
        while (item := self._queue.get()) is not None:
            yield item


Stdin = str | StdinFeed | None


@dataclass
class ExecResult:
    returncode: int | None
    stdout: str
    stderr: str = ""
    timed_out: bool = False
    cancelled: bool = False
    files: dict[str, bytes] = field(default_factory=dict)


class Executor(Protocol):
    python: str

    def execute(
        self,
        files: dict[str, bytes],
        argv: list[str],
        *,
        timeout: float,
        stdin: Stdin = None,
        collect: tuple[str, ...] = (),
        on_output: OutputCallback | None = None,
        cpu_seconds: int | None = None,
        cancel: threading.Event | None = None,
    ) -> ExecResult:
        """Run argv in a fresh folder containing `files`.

        With `on_output`, stdout and stderr are merged and streamed as they arrive.
        `cpu_seconds` caps CPU time (separate from wall-clock `timeout`, so a program
        waiting for typing isn't killed). Setting `cancel` stops the run.
        """
        ...


class LocalExecutor:
    python = sys.executable

    def execute(
        self,
        files: dict[str, bytes],
        argv: list[str],
        *,
        timeout: float,
        stdin: Stdin = None,
        collect: tuple[str, ...] = (),
        on_output: OutputCallback | None = None,
        cpu_seconds: int | None = None,  # not enforced locally (no ulimit on Windows)
        cancel: threading.Event | None = None,
    ) -> ExecResult:
        with tempfile.TemporaryDirectory(prefix="hoss-") as tmp:
            work = Path(tmp)
            for name, data in files.items():
                (work / name).write_bytes(data)
            result = run_process(
                argv, cwd=work, timeout=timeout, stdin=stdin, on_output=on_output, cancel=cancel
            )
            for name in collect:
                if (work / name).exists():
                    result.files[name] = (work / name).read_bytes()
            return result


class DockerSession:
    """Executor bound to one running sandbox container."""

    python = "python"

    def __init__(self, container: str):
        self.container = container

    def execute(
        self,
        files: dict[str, bytes],
        argv: list[str],
        *,
        timeout: float,
        stdin: Stdin = None,
        collect: tuple[str, ...] = (),
        on_output: OutputCallback | None = None,
        cpu_seconds: int | None = None,
        cancel: threading.Event | None = None,
    ) -> ExecResult:
        run_dir = f"/work/run-{uuid.uuid4().hex[:12]}"
        self._upload(run_dir, files)
        try:
            # The in-container `timeout` is what actually stops runaway code: killing the
            # host-side `docker exec` would leave the process running in the container.
            # `timeout` runs the program in its own process group; its pid is saved so
            # a cancel can kill the whole group.
            limit = f"ulimit -t {cpu_seconds}; " if cpu_seconds else ""
            script = f'echo $$ > .pid; {limit}exec timeout -k 2 {timeout:g} "$@"'
            cmd = [
                "docker", "exec", "-i", "-w", run_dir, self.container,
                "sh", "-c", script, "sh", *argv,
            ]  # fmt: skip
            result = run_process(
                cmd,
                timeout=timeout + DOCKER_GRACE_S,
                stdin=stdin,
                on_output=on_output,
                cancel=cancel,
                on_cancel=lambda: self._kill_group(run_dir),
            )
            if result.returncode == TIMEOUT_EXIT or result.returncode in CPU_LIMIT_EXITS:
                result.timed_out = True
            for name in collect:
                read = subprocess.run(
                    ["docker", "exec", self.container, "cat", f"{run_dir}/{name}"],
                    capture_output=True,
                )
                if read.returncode == 0:
                    result.files[name] = read.stdout
            return result
        finally:
            subprocess.run(
                ["docker", "exec", self.container, "rm", "-rf", run_dir], capture_output=True
            )

    def _kill_group(self, run_dir: str) -> None:
        pid_file = shlex.quote(f"{run_dir}/.pid")
        subprocess.run(
            ["docker", "exec", self.container, "sh", "-c", f"kill -KILL -$(cat {pid_file})"],
            capture_output=True,
        )

    def _upload(self, run_dir: str, files: dict[str, bytes]) -> None:
        # `docker cp` can't write into the tmpfs workspace, so stream a tar through exec.
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for name, data in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
        proc = subprocess.run(
            ["docker", "exec", "-i", self.container, "sh", "-c",
             f"mkdir -p {run_dir} && tar -x -C {run_dir}"],
            input=buffer.getvalue(),
            capture_output=True,
        )  # fmt: skip
        if proc.returncode != 0:
            raise RuntimeError(f"upload to sandbox failed: {proc.stderr.decode(errors='replace')}")


def run_process(
    cmd: list[str],
    *,
    timeout: float,
    cwd: Path | None = None,
    stdin: Stdin = None,
    on_output: OutputCallback | None = None,
    cancel: threading.Event | None = None,
    on_cancel: Callable[[], None] | None = None,
) -> ExecResult:
    # Pipes are binary on purpose: text mode on Windows turns "\n" into "\r\n", which
    # Linux sandboxes would then see inside input().
    if on_output is None and cancel is None and not isinstance(stdin, StdinFeed):
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                input=(stdin or "").encode("utf-8"),
                capture_output=True,
                timeout=timeout,
                env=_child_env(),
            )
        except subprocess.TimeoutExpired as e:
            return ExecResult(None, _decode(e.stdout), _decode(e.stderr), timed_out=True)
        return ExecResult(proc.returncode, _decode(proc.stdout), _decode(proc.stderr))

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=_child_env(),
    )
    killed = threading.Event()
    finished = threading.Event()
    cancelled = threading.Event()

    def _kill() -> None:
        killed.set()
        proc.kill()

    def _watch_cancel() -> None:
        assert cancel is not None
        while not finished.is_set():
            if cancel.wait(0.2):
                cancelled.set()
                if on_cancel:
                    on_cancel()
                proc.kill()
                return

    def _feed_stdin() -> None:
        assert proc.stdin
        try:
            for text in stdin if isinstance(stdin, StdinFeed) else [stdin or ""]:
                proc.stdin.write(text.encode("utf-8"))
                proc.stdin.flush()
            proc.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass  # program exited without reading all its input

    timer = threading.Timer(timeout, _kill)
    timer.start()
    threading.Thread(target=_feed_stdin, daemon=True).start()
    if cancel is not None:
        threading.Thread(target=_watch_cancel, daemon=True).start()
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    chunks: list[str] = []
    try:
        assert proc.stdout
        while chunk := proc.stdout.read1(4096):
            text = decoder.decode(chunk).replace("\r\n", "\n")
            if text:
                chunks.append(text)
                if on_output:
                    on_output(text)
        proc.wait()
    finally:
        finished.set()
        timer.cancel()
        if isinstance(stdin, StdinFeed):
            stdin.close()  # unblock the feeder thread
    return ExecResult(
        proc.returncode,
        "".join(chunks),
        timed_out=killed.is_set(),
        cancelled=cancelled.is_set(),
    )


def _decode(data: bytes | None) -> str:
    # Normalise line endings so local (Windows) and sandbox (Linux) output compare equal.
    return (data or b"").decode("utf-8", errors="replace").replace("\r\n", "\n")


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
