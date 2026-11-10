from dojo_checks import assert_image, docker


def test_runs_as_app():
    assert_image("whoami:1")
    out = docker("run", "--rm", "whoami:1")
    assert out.startswith("running as app"), f"it printed {out!r}"
