from hoss_checks import assert_image, docker


def test_default_greeting():
    assert_image("greet:2")
    assert docker("run", "--rm", "greet:2") == "Hello, world"


def test_custom_name():
    assert docker("run", "--rm", "greet:2", "Ada") == "Hello, Ada"
