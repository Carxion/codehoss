import shutil
import tempfile
from pathlib import Path

from hoss_checks import docker, lab_dir, sh


def test_no_tests_in_final_image():
    found = docker("run", "--rm", "calc:1", "sh", "-c", "ls /app")
    assert "test_app.py" not in found.split(), (
        "test_app.py is in calc:1; add it only in the test stage"
    )


def test_test_stage_catches_a_bug():
    work = Path(tempfile.mkdtemp()) / "broken"
    shutil.copytree(lab_dir(), work)
    app = work / "app.py"
    app.write_text(app.read_text().replace("return a + b", "return a - b"))
    proc = sh(f"docker build -q --target test {work}", timeout=120)
    assert proc.returncode != 0, (
        "With add() broken, --target test still built: does the test stage RUN the tests?"
    )
