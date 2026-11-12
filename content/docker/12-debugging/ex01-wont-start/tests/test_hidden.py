from hoss_checks import inspect_container


def test_running_from_fixed_image():
    info = inspect_container("fixme")
    assert info["Config"]["Image"] == "fixme:1" and info["State"]["Running"]
