from dojo_checks import assert_image, docker, sh


def test_final_image_runs():
    assert_image("calc:1")
    assert docker("run", "--rm", "calc:1") == "2 + 3 = 5"


def test_test_stage_builds():
    proc = sh("docker build -q --target test .", timeout=120)
    assert proc.returncode == 0, "docker build --target test . failed:\n" + proc.stderr[-400:]
