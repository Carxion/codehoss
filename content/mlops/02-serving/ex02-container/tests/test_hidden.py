from hoss_checks import sh


def test_slim_image():
    out = sh("docker run --rm house-api:1 ls", timeout=60).stdout.split()
    assert "model" in out and "serve.py" in out, f"the image has {out}"
    assert "data" not in out and "train.py" not in out, (
        "only the model should come from the train stage"
    )
