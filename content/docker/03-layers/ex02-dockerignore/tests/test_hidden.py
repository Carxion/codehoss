from dojo_checks import docker, lab_file


def test_app_still_there():
    assert docker("run", "--rm", "site:1") == "site is up"


def test_dockerignore_written():
    text = lab_file(".dockerignore")
    assert ".env" in text
