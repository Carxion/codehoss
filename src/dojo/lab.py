"""Labs: hands-on modules where learners use real tools (Docker and Kubernetes).

A lab session is the usual locked-down session container plus a private Docker engine
(the official docker:dind image) on an internal network with no internet. The session
reaches the engine as tcp://docker:2375; nothing else can. The engine needs
--privileged, which is why it gets its own container, memory/pids limits and no
network out, and is thrown away with the session. Hosts with the sysbox runtime can set
DOJO_LAB_RUNTIME=sysbox-runc to run it unprivileged.

Kubernetes labs add a single-node k3s cluster (reachable as https://k3s:6443, NodePorts as
http://k3s:PORT) and a registry inside the engine at docker:5000, so learners build with
docker, push, and deploy. Nothing is pulled: k3s's system images and the module's base
images are copied into its image folder before it starts.

Each lab exercise gets a folder in the session (/work/<name>) seeded from its files/;
the browser edits those files and runs commands in a terminal (dojo._term), and checks
inspect real state: files, images, containers, cluster objects, HTTP responses.
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
K3S_IMAGE = "rancher/k3s:v1.37.1-k3s1"
HELM_IMAGE = "alpine/helm:3.19.0"  # only its helm binary is used (copied into dojo-lab)
# What k3s v1.37.1 pulls at start with traefik, metrics-server and helm disabled, plus
# the local-path provisioner's helper (it creates PersistentVolume folders) and our own
# ingress controller.
INGRESS_IMAGE = "traefik:v3.6.2"
K3S_SYSTEM_IMAGES = [
    "rancher/mirrored-pause:3.10.2",
    "rancher/mirrored-coredns-coredns:1.14.7",
    "rancher/local-path-provisioner:v0.0.37",
    "rancher/mirrored-library-busybox:1.37.0",
    INGRESS_IMAGE,
]
# k3s's bundled Traefik installs through its Helm controller (more images, slower start),
# so labs run a plain Traefik instead, applied by k3s from its manifests folder at start.
# It answers on port 80 of the node: Ingress rules are reachable at http://k3s/.
INGRESS_MANIFEST = f"""apiVersion: v1
kind: ServiceAccount
metadata:
  name: traefik
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: traefik
rules:
- apiGroups: [""]
  resources: [services, secrets, nodes]
  verbs: [get, list, watch]
- apiGroups: [discovery.k8s.io]
  resources: [endpointslices]
  verbs: [get, list, watch]
- apiGroups: [networking.k8s.io]
  resources: [ingresses, ingressclasses]
  verbs: [get, list, watch]
- apiGroups: [networking.k8s.io]
  resources: [ingresses/status]
  verbs: [update]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: traefik
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: traefik
subjects:
- kind: ServiceAccount
  name: traefik
  namespace: kube-system
---
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata:
  name: traefik
  annotations:
    ingressclass.kubernetes.io/is-default-class: "true"
spec:
  controller: traefik.io/ingress-controller
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: traefik
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: traefik
  template:
    metadata:
      labels:
        app: traefik
    spec:
      serviceAccountName: traefik
      containers:
      - name: traefik
        image: {INGRESS_IMAGE}
        args:
        - --entryPoints.web.address=:80
        - --providers.kubernetesingress
        - --global.checkNewVersion=false
        - --global.sendAnonymousUsage=false
        ports:
        - containerPort: 80
          hostPort: 80
        resources:
          requests:
            cpu: 10m
            memory: 32Mi
          limits:
            memory: 128Mi
"""
K3S_MEMORY = "1500m"
CLUSTER_START_TIMEOUT_S = 120
REGISTRY_IMAGE = "registry:3.1.2"
REGISTRY = "docker:5000"
KUBECONFIG = "/tmp/.kube/config"  # HOME is /tmp in session images
TERM_SOURCE = (Path(__file__).parent / "_term.py").read_text(encoding="utf-8")
MAX_FILE_BYTES = 256 * 1024
MAX_FILES = 40


class LabError(RuntimeError):
    pass


def images_to_pull(kinds: set[str], lab_images: list[str]) -> list[str]:
    """Everything labs of these kinds run, which must be on the host beforehand."""
    if not kinds:
        return []
    images = {DIND_IMAGE, *lab_images}
    if "kubernetes" in kinds:
        images |= {K3S_IMAGE, REGISTRY_IMAGE, *K3S_SYSTEM_IMAGES}
    return sorted(images)


# --- the engine (and cluster) --------------------------------------------------------


def engine_names(container: str) -> tuple[str, str]:
    """(engine container, network) for a session container."""
    return f"{container}-docker", f"{container}-net"


def cluster_name(container: str) -> str:
    return f"{container}-k3s"


def start_engine(
    container: str, labels: list[str], kind: str = "docker", images: list[str] | None = None
) -> str:
    """Create the network, engine (and cluster) for a session; returns the network name.
    The session container is started on that network afterwards; wait_and_preload
    finishes the job once it's running."""
    engine, network = engine_names(container)
    _docker("network", "create", "--internal", *labels, network)
    runtime = os.environ.get("DOJO_LAB_RUNTIME")
    isolation = ["--runtime", runtime] if runtime else ["--privileged"]
    insecure = ["--insecure-registry", REGISTRY] if kind == "kubernetes" else []
    _docker(
        "run", "--detach", "--name", engine, *labels, *isolation,
        "--network", network, "--network-alias", "docker",
        "--env", "DOCKER_TLS_CERTDIR=",
        "--memory", ENGINE_MEMORY, "--pids-limit", "1024", "--cpus", "2",
        DIND_IMAGE, "--host", "tcp://0.0.0.0:2375", *insecure,
    )  # fmt: skip
    if kind == "kubernetes":
        _create_cluster(container, labels, isolation, network, images or [])
    return network


def _create_cluster(
    container: str, labels: list[str], isolation: list[str], network: str, images: list[str]
) -> None:
    cluster = cluster_name(container)
    # An internal network has no default route, and k3s refuses to pick a node IP
    # without one. There's nothing behind it, so a route via eth0 changes nothing else.
    script = (
        "ip route add default dev eth0 2>/dev/null; exec /bin/k3s server "
        "--disable traefik --disable metrics-server --disable-helm-controller "
        "--tls-san k3s --write-kubeconfig-mode 644"
    )
    _docker(
        "create", "--name", cluster, *labels, *isolation,
        "--network", network, "--network-alias", "k3s",
        "--memory", K3S_MEMORY, "--pids-limit", "2048", "--cpus", "2",
        "--entrypoint", "sh", K3S_IMAGE, "-c", script,
    )  # fmt: skip
    saved = subprocess.run(["docker", "save", *K3S_SYSTEM_IMAGES, *images], capture_output=True)
    if saved.returncode != 0:
        raise LabError(f"could not prepare cluster images: {saved.stderr.decode(errors='replace')}")
    registries = f'mirrors:\n  "{REGISTRY}":\n    endpoint: ["http://{REGISTRY}"]\n'.encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, data in [
            ("var/lib/rancher/k3s/agent/images/lab.tar", saved.stdout),
            ("etc/rancher/k3s/registries.yaml", registries),
            ("var/lib/rancher/k3s/server/manifests/dojo-ingress.yaml", INGRESS_MANIFEST.encode()),
        ]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    copied = subprocess.run(
        ["docker", "cp", "-", f"{cluster}:/"], input=buffer.getvalue(), capture_output=True
    )
    if copied.returncode != 0:
        raise LabError(f"could not prepare the cluster: {copied.stderr.decode(errors='replace')}")
    _docker("start", cluster)


def wait_and_preload(container: str, images: list[str], kind: str = "docker") -> None:
    """Wait for the engine to answer, copy in the module's base images, and for
    Kubernetes labs start the registry and wait for the cluster."""
    engine, _ = engine_names(container)
    deadline = time.monotonic() + ENGINE_START_TIMEOUT_S
    while subprocess.run(
        ["docker", "exec", engine, "docker", "info"], capture_output=True
    ).returncode:
        if time.monotonic() > deadline:
            raise LabError("the lab's Docker engine didn't start in time")
        time.sleep(0.5)
    load_images = [*images, REGISTRY_IMAGE] if kind == "kubernetes" else images
    if load_images:
        save = subprocess.Popen(["docker", "save", *load_images], stdout=subprocess.PIPE)
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
    if kind == "kubernetes":
        _docker(
            "exec", engine, "docker", "run", "--detach", "--name", "registry",
            "--label", "dojo.keep=1", "--restart", "always", "-p", "5000:5000", REGISTRY_IMAGE,
        )  # fmt: skip
        _wait_for_cluster(container)


def _wait_for_cluster(container: str) -> None:
    cluster = cluster_name(container)
    deadline = time.monotonic() + CLUSTER_START_TIMEOUT_S
    ready = ["kubectl", "-n", "kube-system", "rollout", "status", "deploy/coredns", "--timeout=5s"]
    while subprocess.run(["docker", "exec", cluster, *ready], capture_output=True).returncode:
        if time.monotonic() > deadline:
            raise LabError("the lab's Kubernetes cluster didn't start in time")
        time.sleep(1)
    config = subprocess.run(
        ["docker", "exec", cluster, "cat", "/etc/rancher/k3s/k3s.yaml"], capture_output=True
    ).stdout.replace(b"https://127.0.0.1:6443", b"https://k3s:6443")
    upload(container, posixpath.dirname(KUBECONFIG), {posixpath.basename(KUBECONFIG): config})
    _exec(container, "chmod", "600", KUBECONFIG)


def stop_engine(container: str) -> None:
    engine, network = engine_names(container)
    # --volumes: the engine and k3s keep their state in anonymous volumes.
    subprocess.run(
        ["docker", "rm", "--force", "--volumes", engine, cluster_name(container)],
        capture_output=True,
    )
    subprocess.run(["docker", "network", "rm", network], capture_output=True)


RESET_SCRIPT = """
for id in $(docker ps -aq); do
  keep=$(docker inspect -f '{{index .Config.Labels "dojo.keep"}}' "$id")
  [ "$keep" = 1 ] || docker rm -f "$id"
done >/dev/null
docker network prune -f >/dev/null
docker volume prune -af >/dev/null
if [ -f KUBECONFIG ]; then
  namespaces=$(kubectl get ns -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' |
    grep -vxE 'default|kube-system|kube-public|kube-node-lease')
  # Waits, so the next exercise can create a namespace with the same name.
  [ -z "$namespaces" ] || kubectl delete ns $namespaces --timeout=90s
  kubectl delete deploy,sts,ds,job,cronjob,pod,svc,cm,secret,pvc,ing,quota,limits \
    --all -n default --now
fi >/dev/null 2>&1
true
""".replace("KUBECONFIG", KUBECONFIG)


def reset_engine(container: str) -> None:
    """Remove everything the learner made (containers, networks, volumes, cluster
    objects); keep images and the lab's own registry."""
    subprocess.run(["docker", "exec", container, "sh", "-c", RESET_SCRIPT], capture_output=True)


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
