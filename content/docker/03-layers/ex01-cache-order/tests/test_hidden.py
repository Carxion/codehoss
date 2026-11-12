import re
import shutil
import tempfile
from pathlib import Path

from hoss_checks import lab_dir, sh


def test_code_change_keeps_setup_cached():
    work = Path(tempfile.mkdtemp()) / "copy"
    shutil.copytree(lab_dir(), work)
    first = sh(f"docker build --progress=plain -t words:cachecheck {work}", timeout=120)
    assert first.returncode == 0, first.stderr[-500:]
    with open(work / "app.py", "a") as f:
        f.write("# a small code change\n")
    second = sh(f"docker build --progress=plain -t words:cachecheck {work}", timeout=120)
    assert second.returncode == 0, second.stderr[-500:]
    step = re.search(r"#(\d+) \[[^\]]*\] RUN python setup\.py", second.stderr)
    assert step, "the Dockerfile should RUN python setup.py"
    assert f"#{step.group(1)} CACHED" in second.stderr, (
        "Changing app.py reran the slow setup step. Copy app.py after RUN python setup.py."
    )
