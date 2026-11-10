from dojo_checks import assert_image, inspect_container


def test_env_default_in_image():
    env = assert_image("greeter-web:1")["Config"].get("Env") or []
    assert "PORT=8000" in env, "set ENV PORT=8000 in the Dockerfile"


def test_one_image_two_containers():
    for name in ("hello", "hola"):
        assert inspect_container(name)["Config"]["Image"] == "greeter-web:1"
