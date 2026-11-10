from dojo_checks import assert_image, docker, lab_file


def test_uses_python_312():
    version = docker("run", "--rm", "--entrypoint", "python", "greeter:1", "--version")
    assert version.startswith("Python 3.12"), f"the image has {version}; start FROM python:3.12-alpine"


def test_dockerfile_has_the_basics():
    text = lab_file("Dockerfile").upper()
    for word in ("FROM", "COPY", "CMD"):
        assert word in text, f"the Dockerfile needs a {word} instruction"


def test_runs_from_workdir():
    config = assert_image("greeter:1")["Config"]
    assert config.get("WorkingDir") not in ("", "/"), "set a WORKDIR so the app isn't dumped in /"
