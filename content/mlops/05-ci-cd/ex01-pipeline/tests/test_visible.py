import json

from dojo_checks import lab_dir, sh


def plan(branch):
    out = sh(f"cd {lab_dir()} && python ci.py --plan --branch {branch}")
    assert out.returncode == 0, f"ci.py --plan failed: {(out.stderr or out.stdout)[-400:]}"
    data = json.loads(out.stdout)
    return data["stages"], {j["job"]: j for j in data["jobs"]}


def test_stages_and_rules():
    stages, jobs = plan("main")
    expected = {
        "unit-tests": "test",
        "train": "train",
        "quality-gate": "evaluate",
        "build": "build",
        "deploy": "deploy",
    }
    assert {name: j["stage"] for name, j in jobs.items()} == expected, (
        f"jobs and stages: {[(n, j['stage']) for n, j in jobs.items()]}"
    )
    assert all(j["decision"] == "run" for j in jobs.values()), "on main every job should run"
    _, feature = plan("feature/x")
    skipped = {n for n, j in feature.items() if j["decision"] == "skip"}
    assert skipped == {"build", "deploy"}, (
        f"on a feature branch these are skipped: {sorted(skipped)}"
    )
