"""Sandbox images and per-learner session containers.

Every session is one long-lived container started from its module's image with:
no network, a read-only root filesystem, a small writable tmpfs workspace, a
non-root user with no capabilities, and CPU / memory / process limits.
Code runs inside it via `docker exec` (see dojo.executors.DockerSession).
"""

from __future__ import annotations

import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from dojo.executors import DockerSession
from dojo.registry import Content

BASE_IMAGE = "python:3.12-slim"
LABEL = "dojo.session"
# The grader needs pytest in every image, whatever the module declares.
GRADER_PACKAGES = ["pytest>=8"]


class SandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class Limits:
    memory: str = "256m"
    cpus: str = "1"
    pids: int = 128
    workspace: str = "64m"


DEFAULT_LIMITS = Limits()


@dataclass
class Session:
    id: str
    module_id: str
    container: str
    executor: DockerSession
    created: float = field(default_factory=time.monotonic)
    last_used: float = field(default_factory=time.monotonic)


def docker_available() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def image_exists(image: str) -> bool:
    proc = subprocess.run(["docker", "image", "inspect", image], capture_output=True)
    return proc.returncode == 0


def image_specs(content: Content) -> dict[str, list[str]]:
    """Image name -> packages, merged across every module that uses that image."""
    specs: dict[str, list[str]] = {}
    for module in content.modules.values():
        packages = specs.setdefault(module.spec.sandbox.image, list(GRADER_PACKAGES))
        packages += [p for p in module.spec.sandbox.packages if p not in packages]
    return specs


def dockerfile(packages: list[str]) -> str:
    quoted = " ".join(f"'{p}'" for p in packages)
    return (
        f"FROM {BASE_IMAGE}\n"
        f"RUN pip install --no-cache-dir {quoted}\n"
        "RUN useradd --uid 1000 --create-home learner\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 HOME=/tmp\n"
        "USER learner\n"
        "WORKDIR /work\n"
    )


def build_image(image: str, packages: list[str], on_output: Callable[[str], None] = print) -> None:
    proc = subprocess.Popen(
        ["docker", "build", "--progress=plain", "-t", image, "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdin and proc.stdout
    proc.stdin.write(dockerfile(packages))
    proc.stdin.close()
    for line in proc.stdout:
        on_output(line.rstrip())
    if proc.wait() != 0:
        raise SandboxError(f"docker build failed for {image}")


class SessionManager:
    def __init__(
        self,
        content: Content,
        *,
        limits: Limits = DEFAULT_LIMITS,
        idle_timeout_s: float = 15 * 60,
        max_sessions: int = 20,
    ):
        self.content = content
        self.limits = limits
        self.idle_timeout_s = idle_timeout_s
        self.max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, module_id: str) -> Session:
        module = self.content.modules.get(module_id)
        if module is None:
            raise KeyError(module_id)
        sandbox = module.spec.sandbox
        if sandbox.network != "none":
            raise SandboxError("network allowlists are not supported yet (planned for M4)")
        if not image_exists(sandbox.image):
            raise SandboxError(f"image '{sandbox.image}' not found; run `dojo build-images`")
        with self._lock:
            if len(self._sessions) >= self.max_sessions:
                raise SandboxError("too many active sessions; try again later")

        session_id = uuid.uuid4().hex
        container = f"dojo-{session_id[:12]}"
        lim = self.limits
        cmd = [
            "docker", "run", "--detach", "--init",
            "--name", container,
            "--label", f"{LABEL}={session_id}",
            "--label", f"dojo.module={module_id}",
            "--network", "none",
            "--read-only",
            "--tmpfs", f"/work:rw,size={lim.workspace},uid=1000,gid=1000,mode=0700",
            "--tmpfs", "/tmp:rw,size=16m,uid=1000,gid=1000,mode=0700",
            "--user", "1000:1000",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--memory", lim.memory, "--memory-swap", lim.memory,
            "--cpus", lim.cpus,
            "--pids-limit", str(lim.pids),
            sandbox.image,
            "sleep", "infinity",
        ]  # fmt: skip
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise SandboxError(f"could not start sandbox: {proc.stderr.strip()}")

        session = Session(session_id, module_id, container, DockerSession(container))
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions[session_id]
            session.last_used = time.monotonic()
            return session

    def close(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is not None:
            subprocess.run(["docker", "rm", "--force", session.container], capture_output=True)

    def reap_idle(self) -> list[str]:
        cutoff = time.monotonic() - self.idle_timeout_s
        with self._lock:
            idle = [s.id for s in self._sessions.values() if s.last_used < cutoff]
        for session_id in idle:
            self.close(session_id)
        return idle

    def close_all(self) -> None:
        with self._lock:
            ids = list(self._sessions)
        for session_id in ids:
            self.close(session_id)

    @staticmethod
    def remove_orphans() -> int:
        """Remove session containers left behind by a previous run of the server."""
        proc = subprocess.run(
            ["docker", "ps", "--all", "--quiet", "--filter", f"label={LABEL}"],
            capture_output=True,
            text=True,
        )
        ids = proc.stdout.split()
        if ids:
            subprocess.run(["docker", "rm", "--force", *ids], capture_output=True)
        return len(ids)
