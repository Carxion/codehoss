"""Labs: file handling and image/session wiring (fast), plus a real lab session (Docker)."""

import time

import pytest
from conftest import REPO

from dojo import lab
from dojo.grader import grade_lab
from dojo.registry import load_content
from dojo.sandbox import (
    Limits,
    SessionManager,
    docker_available,
    dockerfile,
    image_exists,
    lockdown_flags,
)


@pytest.fixture(scope="module")
def content():
    return load_content(REPO / "content")


@pytest.mark.parametrize(
    "path", ["Dockerfile", "api/app.py", ".dockerignore", "/compose.yaml", "a/../b.txt"]
)
def test_safe_paths(path):
    clean = lab.safe_path(path)
    assert not clean.startswith(("/", ".."))


@pytest.mark.parametrize("path", ["", "..", "../etc/passwd", "a/../../x", ".", "x\x00y"])
def test_unsafe_paths_rejected(path):
    with pytest.raises(ValueError):
        lab.safe_path(path)


def test_lab_exercises_are_detected(content):
    exercise = content.exercise("docker.first-image")
    assert exercise.is_lab
    assert lab.lab_dir(exercise) == "/work/first-image"
    assert all(p.exists() for p in exercise.required_files)
    assert not any(ex.is_lab for ex in content.modules["python-basics"].exercises())


def test_lab_image_gets_docker_cli_only_when_asked():
    assert "docker-buildx" not in dockerfile(["pytest"])
    lab_file = dockerfile(["pytest"], with_lab=True)
    assert f"COPY --from={lab.CLI_IMAGE}" in lab_file
    assert f"DOCKER_HOST={lab.ENGINE_HOST}" in lab_file


def test_lockdown_keeps_everything_but_the_network():
    default, labbed = lockdown_flags(Limits()), lockdown_flags(Limits(), "dojo-x-net")
    assert default[default.index("--network") + 1] == "none"
    assert labbed[labbed.index("--network") + 1] == "dojo-x-net"
    for flag in ("--read-only", "--cap-drop", "--security-opt", "--pids-limit"):
        assert flag in labbed


# --- a real lab -------------------------------------------------------------------

needs_lab = pytest.mark.skipif(
    not (docker_available() and image_exists("dojo-lab") and image_exists(lab.DIND_IMAGE)),
    reason="needs Docker, dojo-lab and docker:dind (run `dojo build-images`)",
)


@pytest.fixture(scope="module")
def lab_session(content):
    manager = SessionManager(content)
    session = manager.create("docker")
    yield session
    manager.close(session.id)


@pytest.mark.docker
@needs_lab
def test_lab_session_has_engine_but_no_internet(lab_session):
    run = lab_session.executor.execute(
        {},
        [
            "sh",
            "-c",
            "docker images; curl -sm 3 http://example.com || echo offline",
        ],
        timeout=30,
    )
    assert "python" in run.stdout and "3.12-alpine" in run.stdout
    assert "offline" in run.stdout


@pytest.mark.docker
@needs_lab
def test_seed_grade_and_reset(content, lab_session):
    exercise = content.exercise("docker.first-container")
    container = lab_session.container
    lab.seed(container, exercise)
    assert "README.md" in lab.read_files(container, lab.lab_dir(exercise))
    assert not grade_lab(exercise, lab.lab_dir(exercise), executor=lab_session.executor).passed
    assert lab.run_solution(container, exercise).returncode == 0
    assert grade_lab(exercise, lab.lab_dir(exercise), executor=lab_session.executor).passed
    lab.reset_engine(container)
    assert not grade_lab(exercise, lab.lab_dir(exercise), executor=lab_session.executor).passed


@pytest.mark.docker
@needs_lab
def test_files_written_and_kept(content, lab_session):
    exercise = content.exercise("docker.first-image")
    container = lab_session.container
    lab.seed(container, exercise)
    lab.write_file(container, exercise, "Dockerfile", "FROM scratch\n")
    lab.seed(container, exercise)  # reopening never overwrites work
    assert lab.read_files(container, lab.lab_dir(exercise))["Dockerfile"] == "FROM scratch\n"
    lab.seed(container, exercise, force=True)
    assert "FROM scratch" not in lab.read_files(container, lab.lab_dir(exercise))["Dockerfile"]


@pytest.mark.docker
@needs_lab
def test_terminal_runs_commands(lab_session):
    chunks: list[bytes] = []
    shell = lab.Terminal(lab_session.container, "/work", chunks.append)
    try:
        shell.send({"r": [100, 30]})
        shell.send({"i": "echo $((40 + 2)); stty size\n"})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and b"30 100" not in b"".join(chunks):
            time.sleep(0.2)
        out = b"".join(chunks).decode(errors="replace")
        assert "42" in out and "30 100" in out, out
    finally:
        shell.close()


def test_closing_a_lab_removes_engine_and_network():
    # Unit-level: engine names are derived from the session container name.
    assert lab.engine_names("dojo-abc") == ("dojo-abc-docker", "dojo-abc-net")


def test_images_to_pull():
    assert lab.images_to_pull(set(), ["alpine:3.22"]) == []
    docker_only = lab.images_to_pull({"docker"}, ["alpine:3.22"])
    assert lab.DIND_IMAGE in docker_only and lab.K3S_IMAGE not in docker_only
    with_k8s = lab.images_to_pull({"docker", "kubernetes"}, [])
    assert {lab.K3S_IMAGE, lab.REGISTRY_IMAGE, *lab.K3S_SYSTEM_IMAGES} <= set(with_k8s)


needs_cluster = pytest.mark.skipif(
    not (docker_available() and image_exists("dojo-lab") and image_exists(lab.K3S_IMAGE)),
    reason="needs Docker, dojo-lab and the k3s images (run `dojo build-images`)",
)


@pytest.fixture(scope="module")
def cluster_session(content):
    manager = SessionManager(content)
    session = manager.create("kubernetes")
    yield session
    manager.close(session.id)


@pytest.mark.docker
@needs_cluster
def test_cluster_ready_and_reset(cluster_session):
    def sh(script):
        return cluster_session.executor.execute({}, ["sh", "-c", script], timeout=90).stdout

    assert " Ready " in sh("kubectl get nodes")
    sh("kubectl create deployment demo --image=python:3.12-alpine -- sleep 300")
    assert "demo" in sh("kubectl get deploy")
    lab.reset_engine(cluster_session.container)
    assert "demo" not in sh("kubectl get deploy 2>&1")
    # the lab's registry survives a reset
    assert "registry" in sh("docker ps --format '{{.Names}}'")


@pytest.mark.docker
@needs_cluster
def test_cluster_has_ingress_storage_and_helm(cluster_session):
    def sh(script, timeout=120):
        result = cluster_session.executor.execute({}, ["sh", "-c", script], timeout=timeout)
        return result.stdout + result.stderr

    assert "successfully rolled out" in sh(
        "kubectl -n kube-system rollout status deploy/traefik --timeout=90s"
    )
    # Nothing routed yet: Traefik itself answers 404 on the node's port 80.
    assert sh("curl -s -o /dev/null -w '%{http_code}' http://k3s/") == "404"
    manifest = (
        "apiVersion: v1\nkind: PersistentVolumeClaim\nmetadata: {name: probe}\n"
        "spec: {accessModes: [ReadWriteOnce], resources: {requests: {storage: 1Mi}}}\n"
        "---\n"
        "apiVersion: v1\nkind: Pod\nmetadata: {name: probe}\nspec:\n"
        "  containers: [{name: p, image: python:3.12-alpine, command: [sleep, '300'],"
        " volumeMounts: [{name: d, mountPath: /d}]}]\n"
        "  volumes: [{name: d, persistentVolumeClaim: {claimName: probe}}]\n"
    )
    applied = cluster_session.executor.execute(
        {"probe.yaml": manifest.encode()}, ["kubectl", "apply", "-f", "probe.yaml"], timeout=60
    )
    assert applied.returncode == 0, applied.stderr
    # Binding needs the provisioner's helper image, which is copied in (no internet).
    assert "condition met" in sh("kubectl wait --for=condition=Ready pod/probe --timeout=90s")
    assert sh("kubectl get pvc probe -o jsonpath='{.status.phase}'") == "Bound"
    assert sh("helm version --short").startswith("v3.")
    lab.reset_engine(cluster_session.container)
