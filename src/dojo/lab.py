"""Labs: hands-on modules where learners use real tools (Docker now, Kubernetes next).

A lab session is the usual locked-down session container plus a private Docker engine
(the official docker:dind image) on an internal network with no internet. The session
reaches the engine as tcp://docker:2375; nothing else can. The engine needs
--privileged, which is why it gets its own container, memory/pids limits and no
network out, and is thrown away with the session. Hosts with the sysbox runtime can set
DOJO_LAB_RUNTIME=sysbox-runc to run it unprivileged.

Each lab exercise gets a folder in the session (/work/<name>) seeded from its files/;
the browser edits those files and runs commands in a terminal (dojo._term), and checks
inspect real state: files, images, containers, HTTP responses.
"""

from __future__ import annotations

import io
import json
import os
import posixpath
import subprocess
import tarfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from dojo.registry import LoadedExercise

DIND_IMAGE = "docker:29-dind"
CLI_IMAGE = "docker:29-cli"
ENGINE_HOST = "tcp://docker:2375"
ENGINE_MEMORY = "1g"
ENGINE_START_TIMEOUT_S = 60
TERM_SOURCE = (Path(__file__).parent / "_term.py").read_text(encoding="utf-8")
MAX_FILE_BYTES = 256 * 1024
MAX_FILES = 40


class LabError(RuntimeError):
    pass


# --- the engine -------------------------------------------------------------------


def engine_names(container: str) -> tuple[str, str]:
    """(engine container, network) for a session container."""
    return f"{container}-docker", f"{container}-net"


def start_engine(container: str, labels: list[str]) -> str:
    """Create the network and engine for a session; returns the network name. The
    session container is started on that network afterwards."""
    engine, network = engine_names(container)
    _docker("network", "create", "--internal", *labels, network)
    runtime = os.environ.get("DOJO_LAB_RUNTIME")
    isolation = ["--runtime", runtime] if runtime else ["--privileged"]
    _docker(
        "run", "--detach", "--name", engine, *labels, *isolation,
        "--network", network, "--network-alias", "docker",
        "--env", "DOCKER_TLS_CERTDIR=",
        "--memory", ENGINE_MEMORY, "--pids-limit", "1024", "--cpus", "2",
        DIND_IMAGE, "--host", "tcp://0.0.0.0:2375",
    )  # fmt: skip
    return network


def wait_and_preload(container: str, images: list[str]) -> None:
    """Wait for the engine to answer, then copy in the module's base images."""
    engine, _ = engine_names(container)
    deadline = time.monotonic() + ENGINE_START_TIMEOUT_S
    while subprocess.run(
        ["docker", "exec", engine, "docker", "info"], capture_output=True
    ).returncode:
        if time.monotonic() > deadline:
            raise LabError("the lab's Docker engine didn't start in time")
        time.sleep(0.5)
    if images:
        save = subprocess.Popen(["docker", "save", *images], stdout=subprocess.PIPE)
        load = subprocess.run(
            ["docker", "exec", "-i", engine, "docker", "load", "-q"],
            stdin=save.stdout,
            capture_output=True,
        )
        save.wait()
        if save.returncode or load.returncode:
            raise LabError(
                f"could not copy images into the lab: {load.stderr.decode(errors='replace')}"
            )


def stop_engine(container: str) -> None:
    engine, network = engine_names(container)
    # -v: the engine keeps images and containers in an anonymous volume.
    subprocess.run(["docker", "rm", "--force", "--volumes", engine], capture_output=True)
    subprocess.run(["docker", "network", "rm", network], capture_output=True)


def reset_engine(container: str) -> None:
    """Remove every container, network and volume the learner made; keep images."""
    script = (
        'ids=$(docker ps -aq); [ -z "$ids" ] || docker rm -f $ids >/dev/null; '
        "docker network prune -f >/dev/null; docker volume prune -af >/dev/null"
    )
    subprocess.run(["docker", "exec", container, "sh", "-c", script], capture_output=True)


# --- exercise folders ---------------------------------------------------------------


def lab_dir(exercise: LoadedExercise) -> str:
    return "/work/" + exercise.spec.id.split(".", 1)[1]


def seed(
    container: str, exercise: LoadedExercise, *, solution: bool = False, force: bool = False
) -> None:
    """Copy the exercise's starter files (or its solution) into its folder. Without
    `force`, an existing folder is left alone so learners keep their work."""
    target = lab_dir(exercise)
    if not force and _exec(container, "test", "-d", target).returncode == 0:
        return
    source = exercise.dir / ("solution" if solution else "files")
    files = {
        p.relative_to(source).as_posix(): p.read_bytes()
        for p in sorted(source.rglob("*"))
        if p.is_file()
    }
    # Empty the folder rather than replacing it: a terminal may be sitting in it.
    _exec(container, "sh", "-c", 'mkdir -p "$0" && find "$0" -mindepth 1 -delete', target)
    upload(container, target, files)


def upload(container: str, target: str, files: dict[str, bytes]) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            tar.addfile(info, io.BytesIO(data))
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "sh", "-c", 'mkdir -p "$0" && tar -x -C "$0"', target],
        input=buffer.getvalue(),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise LabError(f"could not write files: {proc.stderr.decode(errors='replace').strip()}")


def read_files(container: str, target: str) -> dict[str, str]:
    """Text files in a lab folder (skipping big and binary ones, and .git)."""
    proc = subprocess.run(
        ["docker", "exec", container, "sh", "-c", 'cd "$0" && tar -c --exclude=.git .', target],
        capture_output=True,
    )
    if proc.returncode != 0:
        return {}
    files: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        for member in tar:
            if not member.isfile() or member.size > MAX_FILE_BYTES or len(files) >= MAX_FILES:
                continue
            data = tar.extractfile(member)
            if data is None:
                continue
            try:
                files[posixpath.normpath(member.name)] = data.read().decode("utf-8")
            except UnicodeDecodeError:
                continue
    return dict(sorted(files.items()))


def safe_path(path: str) -> str:
    """A relative path inside the lab folder, or ValueError."""
    clean = posixpath.normpath(path.strip().lstrip("/"))
    if not path.strip() or clean.startswith("..") or clean == "." or "\x00" in clean:
        raise ValueError(f"'{path}' is not a file name inside the lab folder")
    return clean


def write_file(container: str, exercise: LoadedExercise, path: str, text: str) -> None:
    upload(container, lab_dir(exercise), {safe_path(path): text.encode("utf-8")})


def delete_file(container: str, exercise: LoadedExercise, path: str) -> None:
    _exec(container, "rm", "-f", posixpath.join(lab_dir(exercise), safe_path(path)))


def run_solution(
    container: str, exercise: LoadedExercise, timeout: float = 120
) -> subprocess.CompletedProcess:
    """Run solution.sh in the exercise folder, as a learner would in the terminal."""
    script = (exercise.dir / "solution.sh").read_text(encoding="utf-8")
    return subprocess.run(
        ["docker", "exec", "-w", lab_dir(exercise), container, "bash", "-e", "-c", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _exec(container: str, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "exec", container, *argv], capture_output=True)


def _docker(*argv: str) -> None:
    proc = subprocess.run(["docker", *argv], capture_output=True, text=True)
    if proc.returncode != 0:
        raise LabError(f"docker {argv[0]} failed: {proc.stderr.strip()}")


# --- terminal -----------------------------------------------------------------------


class Terminal:
    """One bash shell in a lab session, bridged to a browser terminal."""

    def __init__(self, container: str, start_dir: str, on_output: Callable[[bytes], None]):
        script = 'exec python -u -c "$0" "$1"'
        self._proc = subprocess.Popen(
            ["docker", "exec", "-i", container, "sh", "-c", script, TERM_SOURCE, start_dir],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self._lock = threading.Lock()
        self._on_output = on_output
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self._proc.stdout
        while chunk := self._proc.stdout.read1(65536):
            self._on_output(chunk)

    def send(self, message: dict) -> None:
        assert self._proc.stdin
        try:
            with self._lock:
                self._proc.stdin.write(json.dumps(message).encode("utf-8") + b"\n")
                self._proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass

    @property
    def alive(self) -> bool:
        return self._proc.poll() is None

    def close(self) -> None:
        if self._proc.stdin:
            try:
                self._proc.stdin.close()
            except OSError:
                pass
        try:
            self._proc.wait(2)
        except subprocess.TimeoutExpired:
            self._proc.kill()
