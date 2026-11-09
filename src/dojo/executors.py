"""Where learner code actually runs.

An executor takes a set of files plus a command, runs it, and hands back the
output and any files asked for. The grader doesn't care which one it gets:

- LocalExecutor: a temp folder on this machine (fast; tests and authoring only)
- DockerSession: a locked-down per-learner container (see dojo.sandbox)
"""

from __future__ import annotations

import codecs
import io
import os
import subprocess
import sys
import tarfile
import tempfile
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

OutputCallback = Callable[[str], None]

# `timeout` (coreutils) exits 124 when it had to stop the command.
TIMEOUT_EXIT = 124
# Extra host-side allowance on top of the in-container timeout for `docker exec` overhead.
DOCKER_GRACE_S = 10.0


@dataclass
class ExecResult:
    returncode: int | None
    stdout: str
    stderr: str = ""
    timed_out: bool = False
    files: dict[str, bytes] = field(default_factory=dict)


class Executor(Protocol):
    python: str

    def execute(
        self,
        files: dict[str, bytes],
        argv: list[str],
        *,
        timeout: float,
        stdin: str | None = None,
        collect: tuple[str, ...] = (),
        on_output: OutputCallback | None = None,
    ) -> ExecResult:
        """Run argv in a fresh folder containing `files`.

        With `on_output`, stdout and stderr are merged and streamed as they arrive.
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
        stdin: str | None = None,
        collect: tuple[str, ...] = (),
        on_output: OutputCallback | None = None,
    ) -> ExecResult:
        with tempfile.TemporaryDirectory(prefix="dojo-") as tmp:
            work = Path(tmp)
            for name, data in files.items():
                (work / name).write_bytes(data)
            result = run_process(argv, cwd=work, timeout=timeout, stdin=stdin, on_output=on_output)
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
        stdin: str | None = None,
        collect: tuple[str, ...] = (),
        on_output: OutputCallback | None = None,
    ) -> ExecResult:
        run_dir = f"/work/run-{uuid.uuid4().hex[:12]}"
        self._upload(run_dir, files)
        try:
            # The in-container timeout is what actually stops runaway code: killing the
            # host-side `docker exec` would leave the process running in the container.
            cmd = [
                "docker", "exec", "-i", "-w", run_dir, self.container,
                "timeout", "-k", "2", f"{timeout:g}", *argv,
            ]  # fmt: skip
            result = run_process(
                cmd, timeout=timeout + DOCKER_GRACE_S, stdin=stdin, on_output=on_output
            )
            if result.returncode == TIMEOUT_EXIT:
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
    stdin: str | None = None,
    on_output: OutputCallback | None = None,
) -> ExecResult:
    # Pipes are binary on purpose: text mode on Windows turns "\n" into "\r\n", which
    # Linux sandboxes would then see inside input().
    if on_output is None:
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

    def _kill() -> None:
        killed.set()
        proc.kill()

    timer = threading.Timer(timeout, _kill)
    timer.start()
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    chunks: list[str] = []
    try:
        assert proc.stdin and proc.stdout
        try:
            proc.stdin.write((stdin or "").encode("utf-8"))
            proc.stdin.close()
        except BrokenPipeError:
            pass  # program exited without reading its input
        while chunk := proc.stdout.read1(4096):
            text = decoder.decode(chunk)
            if text:
                chunks.append(text)
                on_output(text)
        proc.wait()
    finally:
        timer.cancel()
    return ExecResult(proc.returncode, "".join(chunks), timed_out=killed.is_set())


def _decode(data: bytes | None) -> str:
    # Normalise line endings so local (Windows) and sandbox (Linux) output compare equal.
    return (data or b"").decode("utf-8", errors="replace").replace("\r\n", "\n")


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
