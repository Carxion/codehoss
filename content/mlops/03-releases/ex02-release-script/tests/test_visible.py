import json

from hoss_checks import lab_dir, sh


def tags():
    out = sh("curl -s http://docker:5000/v2/house-api/tags/list").stdout
    return set((json.loads(out).get("tags") or []) if out.strip().startswith("{") else [])


def model_version_in(image):
    out = sh(f"docker run --rm {image} cat model/model.json", timeout=120)
    assert out.returncode == 0, f"couldn't run {image}: {out.stderr[-200:]}"
    return json.loads(out.stdout)["version"]


def test_release():
    out = sh(f"cd {lab_dir()} && sh release.sh 1.1.0", timeout=180)
    assert out.returncode == 0, f"sh release.sh 1.1.0 failed: {(out.stderr or out.stdout)[-400:]}"
    assert {"1.1.0", "latest"} <= tags(), f"the registry has {sorted(tags())}"
    assert model_version_in("docker:5000/house-api:1.1.0") == "1.1.0", (
        "pass MODEL_VERSION in as a build argument"
    )
