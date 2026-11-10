import json

from dojo_checks import lab_dir, sh


def tags():
    out = sh("curl -s http://docker:5000/v2/house-api/tags/list").stdout
    return set((json.loads(out).get("tags") or []) if out.strip().startswith("{") else [])


def model_version_in(image):
    out = sh(f"docker run --rm {image} cat model/model.json", timeout=120)
    assert out.returncode == 0, f"couldn't run {image}: {out.stderr[-200:]}"
    return json.loads(out.stdout)["version"]


def test_bad_model_is_not_released():
    out = sh(f"cd {lab_dir()} && MAX_MAE=1 sh release.sh 6.6.6", timeout=180)
    assert out.returncode != 0, (
        "with MAX_MAE=1 the gate should fail the build, and the script should fail"
    )
    assert "6.6.6" not in tags(), "a model that failed the gate was pushed"
