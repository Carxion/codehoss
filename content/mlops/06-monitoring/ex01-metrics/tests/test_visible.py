import shutil
import subprocess

import pytest
from hoss_checks import lab_dir


@pytest.fixture
def project(tmp_path):
    """A copy of the learner's folder, so tests never touch their files."""
    target = tmp_path / "project"
    shutil.copytree(lab_dir(), target, ignore=shutil.ignore_patterns("model", "__pycache__"))
    return target


def run(project, command, **env):
    import os

    return subprocess.run(
        command,
        shell=True,
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, **env},
    )


def start_server(project, port):
    import json
    import os
    import time
    import urllib.request

    trained = run(project, "python train.py")
    assert trained.returncode == 0, f"train.py failed: {trained.stderr[-300:]}"
    proc = subprocess.Popen(
        ["python", "serve.py"],
        cwd=project,
        env={**os.environ, "PORT": str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                json.load(r)
                return proc
        except OSError:
            if proc.poll() is not None:
                raise AssertionError(f"serve.py stopped: {proc.stdout.read()[-400:]}") from None
            time.sleep(0.2)
    proc.kill()
    raise AssertionError("serve.py didn't answer /health")


def call(port, path, body=None):
    import json
    import urllib.error
    import urllib.request

    data = (
        None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    )
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method="POST" if data is not None else "GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_metrics(project):
    server = start_server(project, 18083)
    try:
        for _ in range(2):
            assert call(18083, "/predict", {"sqft": 1500, "bedrooms": 3, "age": 10})[0] == 200
        assert call(18083, "/predict", {"sqft": "big"})[0] == 400
        status, text = call(18083, "/metrics")
        assert status == 200, f"GET /metrics gave {status}"
        lines = [line for line in text.splitlines() if line and not line.startswith("#")]
        assert lines == [
            "predictions_total 2",
            "prediction_errors_total 1",
            'model_info{version="1.0.0"} 1',
        ], lines
    finally:
        server.kill()
