from hoss_checks import assert_image, docker


def test_image_built():
    assert_image("greeter:1")


def test_it_greets():
    out = docker("run", "--rm", "greeter:1")
    assert out == "Hello from greeter", f"the container printed {out!r}"
