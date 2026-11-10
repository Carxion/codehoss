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


def test_passes_a_good_model(project):
    run(project, "python train.py")
    out = run(project, "python check_metrics.py")
    assert out.returncode == 0 and out.stdout.startswith("metrics OK"), (
        f"exit {out.returncode}: {out.stdout!r}"
    )
