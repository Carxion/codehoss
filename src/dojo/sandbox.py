"""Sandbox images and per-learner session containers.

Every session is one long-lived container started from its module's image with:
no network, a read-only root filesystem, a small writable tmpfs workspace, a
non-root user with no capabilities, and CPU / memory / process limits.
Code runs inside it via `docker exec` (see dojo.executors.DockerSession).
The language server (dojo.lsp) gets its own container with the same lockdown.
Lab modules add a private Docker engine on an internal network (see dojo.lab).
"""

from __future__ import annotations

import base64
import dataclasses
import json
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from dojo import lab
from dojo.executors import DockerSession
from dojo.registry import Content

BASE_IMAGE = "python:3.12-slim"
LABEL = "dojo.session"
# Every image needs pytest (grading) and basedpyright (IntelliSense), whatever the
# module declares.
PLATFORM_PACKAGES = ["pytest>=8", "basedpyright>=1.20"]
LIBRARY_DIR = Path("var/library")
LIBRARY_INDEXER = Path(__file__).parent / "_library_indexer.py"


class SandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class Limits:
    memory: str = "256m"
    cpus: str = "1"
    pids: int = 128
    workspace: str = "64m"


LAB_WORKSPACE = "256m"


DEFAULT_LIMITS = Limits()


@dataclass
class Session:
    id: str
    module_id: str
    owner: int | None
    container: str
    executor: DockerSession
    lab: bool = False
    created: float = field(default_factory=time.monotonic)
    last_used: float = field(default_factory=time.monotonic)


def lockdown_flags(limits: Limits, network: str = "none") -> list[str]:
    """`docker run` flags shared by every sandbox container."""
    return [
        "--init",
        "--network", network,
        "--read-only",
        "--tmpfs", f"/work:rw,size={limits.workspace},uid=1000,gid=1000,mode=0700",
        "--tmpfs", "/tmp:rw,size=32m,uid=1000,gid=1000,mode=0700",
        "--user", "1000:1000",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", limits.memory, "--memory-swap", limits.memory,
        "--cpus", limits.cpus,
        "--pids-limit", str(limits.pids),
    ]  # fmt: skip


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
        packages = specs.setdefault(module.spec.sandbox.image, list(PLATFORM_PACKAGES))
        packages += [p for p in module.spec.sandbox.packages if p not in packages]
    return specs


DOJO_AI_SOURCE = Path(__file__).parent / "_dojo_ai.py"


def lab_images(content: Content) -> dict[str, list[str]]:
    """Session image -> base images its lab modules preload (only images with labs)."""
    labs: dict[str, list[str]] = {}
    for module in content.modules.values():
        sandbox = module.spec.sandbox
        if sandbox.lab:
            images = labs.setdefault(sandbox.image, [])
            images += [i for i in sandbox.lab_images if i not in images]
    return labs


# Lab sessions drive the lab's engine with the Docker CLI (and compose/buildx plugins)
# copied from the official image; curl is for poking at the learner's web apps.
LAB_TOOLS = (
    f"COPY --from={lab.CLI_IMAGE} /usr/local/bin/docker /usr/local/bin/docker\n"
    f"COPY --from={lab.CLI_IMAGE} /usr/local/libexec/docker/cli-plugins"
    " /usr/local/libexec/docker/cli-plugins\n"
    # k3s is a multi-call binary: installed under the name kubectl, it is kubectl.
    f"COPY --from={lab.K3S_IMAGE} /bin/k3s /usr/local/bin/kubectl\n"
    "RUN apt-get update && apt-get install -y --no-install-recommends curl procps "
    "&& rm -rf /var/lib/apt/lists/*\n"
    f"ENV DOCKER_HOST={lab.ENGINE_HOST}\n"
)


def dockerfile(packages: list[str], *, with_lab: bool = False) -> str:
    quoted = " ".join(f"'{p}'" for p in packages)
    # dojo_ai is installed into site-packages so imports, IntelliSense and hover docs
    # all work. Inlined as base64 because images build without a context directory.
    dojo_ai = base64.b64encode(DOJO_AI_SOURCE.read_bytes()).decode("ascii")
    install_dojo_ai = (
        "import base64, sysconfig, pathlib; "
        "pathlib.Path(sysconfig.get_paths()['purelib'], 'dojo_ai.py')"
        f".write_bytes(base64.b64decode('{dojo_ai}'))"
    )
    return (
        f"FROM {BASE_IMAGE}\n"
        f"RUN pip install --no-cache-dir {quoted}\n"
        f'RUN python -c "{install_dojo_ai}"\n'
        + (LAB_TOOLS if with_lab else "")
        + "RUN useradd --uid 1000 --create-home learner\n"
        # Agg: charts render to images; there is no display in a sandbox.
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 HOME=/tmp MPLBACKEND=Agg\n"
        # One thread each: BLAS thread pools would count against the pids limit.
        "ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1\n"
        "USER learner\n"
        "WORKDIR /work\n"
    )


def build_image(
    image: str,
    packages: list[str],
    on_output: Callable[[str], None] = print,
    *,
    with_lab: bool = False,
) -> None:
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
    proc.stdin.write(dockerfile(packages, with_lab=with_lab))
    proc.stdin.close()
    for line in proc.stdout:
        on_output(line.rstrip())
    if proc.wait() != 0:
        raise SandboxError(f"docker build failed for {image}")


def build_library_index(content: Content, module_id: str) -> Path:
    """Introspect the module's libraries inside its image -> var/library/<module>.json.

    Generated at build time so the Library Explorer loads instantly, without a session.
    """
    module = content.modules[module_id]
    explorer = module.spec.library_explorer
    names = list(dict.fromkeys(explorer.featured + explorer.modules))
    proc = subprocess.run(
        ["docker", "run", "--rm", "-i", *lockdown_flags(DEFAULT_LIMITS),
         module.spec.sandbox.image, "python", "-", *names],
        input=LIBRARY_INDEXER.read_bytes(),
        capture_output=True,
    )  # fmt: skip
    if proc.returncode != 0:
        raise SandboxError(f"library indexing failed: {proc.stderr.decode(errors='replace')}")
    index = {"featured": explorer.featured, "libraries": json.loads(proc.stdout)}
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    path = LIBRARY_DIR / f"{module_id}.json"
    path.write_text(json.dumps(index), encoding="utf-8")
    return path


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

    def create(self, module_id: str, owner: int | None = None) -> Session:
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
        # The module decides how much memory its sessions need (pandas needs far more
        # than print statements).
        limits = dataclasses.replace(self.limits, memory=sandbox.memory)
        labels = ["--label", f"{LABEL}={session_id}", "--label", f"dojo.module={module_id}"]
        network = "none"
        if sandbox.lab:
            limits = dataclasses.replace(limits, workspace=LAB_WORKSPACE)
            try:
                network = lab.start_engine(container, labels, sandbox.lab, sandbox.lab_images)
            except lab.LabError as e:
                lab.stop_engine(container)
                raise SandboxError(str(e)) from None
        mounts = []
        if module.data_dir is not None:
            mounts = ["--mount", f"type=bind,source={module.data_dir},target=/data,readonly"]
        cmd = [
            "docker", "run", "--detach",
            "--name", container,
            *labels,
            *lockdown_flags(limits, network),
            *mounts,
            sandbox.image,
            "sleep", "infinity",
        ]  # fmt: skip
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            if sandbox.lab:
                lab.stop_engine(container)
            raise SandboxError(f"could not start sandbox: {proc.stderr.strip()}")
        if sandbox.lab:
            try:
                lab.wait_and_preload(container, sandbox.lab_images, sandbox.lab)
            except lab.LabError as e:
                subprocess.run(["docker", "rm", "--force", container], capture_output=True)
                lab.stop_engine(container)
                raise SandboxError(str(e)) from None

        session = Session(
            session_id, module_id, owner, container, DockerSession(container), lab=bool(sandbox.lab)
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def find(self, owner: int, module_id: str) -> Session | None:
        """An owner's existing session for a module, so page reloads reuse it."""
        with self._lock:
            return next(
                (
                    s
                    for s in self._sessions.values()
                    if s.owner == owner and s.module_id == module_id
                ),
                None,
            )

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
            if session.lab:
                lab.stop_engine(session.container)

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
        """Remove sandbox containers left behind by a previous run of the server."""
        proc = subprocess.run(
            ["docker", "ps", "--all", "--quiet", "--filter", f"label={LABEL}"],
            capture_output=True,
            text=True,
        )
        ids = proc.stdout.split()
        if ids:
            # --volumes: lab engines keep their images in an anonymous volume.
            subprocess.run(["docker", "rm", "--force", "--volumes", *ids], capture_output=True)
        networks = subprocess.run(
            ["docker", "network", "ls", "--quiet", "--filter", f"label={LABEL}"],
            capture_output=True,
            text=True,
        ).stdout.split()
        if networks:
            subprocess.run(["docker", "network", "rm", *networks], capture_output=True)
        return len(ids)
