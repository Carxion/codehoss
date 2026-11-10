from dojo_checks import assert_image, docker


def test_user_set_in_image():
    assert assert_image("whoami:1")["Config"].get("User") == "app", "set USER app in the Dockerfile"


def test_not_uid_zero():
    assert docker("run", "--rm", "whoami:1", "id", "-u") != "0"
