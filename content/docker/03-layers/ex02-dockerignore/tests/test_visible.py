from hoss_checks import assert_image, docker


def test_secrets_not_in_image():
    assert_image("site:1")
    files = docker("run", "--rm", "site:1", "ls", "-a").split()
    assert ".env" not in files, ".env (with a password!) is inside the image"
    assert "logs" not in files, "the logs folder is inside the image"
