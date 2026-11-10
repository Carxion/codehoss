import shutil
import subprocess

import pytest
from dojo_checks import lab_dir


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


def test_values(project):
    import json

    run(project, "python train.py", MODEL_VERSION="2.5.0")
    metrics = json.loads((project / "model" / "metrics.json").read_text())
    assert metrics["version"] == "2.5.0", "use VERSION (from MODEL_VERSION)"
    assert (metrics["train_rows"], metrics["test_rows"]) == (200, 50)
    assert 5000 < metrics["mae"] < 25000 and metrics["mae"] == round(metrics["mae"], 2)
