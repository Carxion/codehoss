import json

from hoss_checks import lab_dir, sh


def plan(branch):
    out = sh(f"cd {lab_dir()} && python ci.py --plan --branch {branch}")
    assert out.returncode == 0, f"ci.py --plan failed: {(out.stderr or out.stdout)[-400:]}"
    data = json.loads(out.stdout)
    return data["stages"], {j["job"]: j for j in data["jobs"]}


def test_smoke_test_job():
    stages, jobs = plan("main")
    assert stages[-1] == "verify" and jobs.get("smoke-test", {}).get("stage") == "verify"
    _, feature = plan("feature/x")
    assert feature["smoke-test"]["decision"] == "skip", "smoke-test is main only"
