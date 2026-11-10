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


def test_saves_model_and_metrics(project):
    import json

    out = run(project, "python train.py", MODEL_VERSION="1.0.0")
    assert out.returncode == 0, out.stderr[-400:]
    model = json.loads((project / "model" / "model.json").read_text())
    assert model["version"] == "1.0.0" and model["features"] == ["sqft", "bedrooms", "age"]
    assert len(model["weights"]) == 4, "weights: the intercept plus one per feature"
    metrics = json.loads((project / "model" / "metrics.json").read_text())
    assert set(metrics) >= {"version", "mae", "train_rows", "test_rows"}, (
        f"metrics.json has {sorted(metrics)}"
    )
