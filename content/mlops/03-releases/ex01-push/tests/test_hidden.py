import json

from hoss_checks import sh


def tags():
    out = sh("curl -s http://docker:5000/v2/house-api/tags/list").stdout
    return set((json.loads(out).get("tags") or []) if out.strip().startswith("{") else [])


def model_version_in(image):
    out = sh(f"docker run --rm {image} cat model/model.json", timeout=120)
    assert out.returncode == 0, f"couldn't run {image}: {out.stderr[-200:]}"
    return json.loads(out.stdout)["version"]


def test_it_is_the_model():
    assert model_version_in("docker:5000/house-api:1.0.0") == "1.0.0"
