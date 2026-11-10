from dojo_checks import assert_image, inspect_container


def test_container_from_image():
    info = inspect_container("web")
    assert info["Config"]["Image"] == "web:1", "run the container from your web:1 image"
    assert info["State"]["Running"]


def test_exposes_8000():
    assert "8000/tcp" in (assert_image("web:1")["Config"].get("ExposedPorts") or {}), "add EXPOSE 8000"
