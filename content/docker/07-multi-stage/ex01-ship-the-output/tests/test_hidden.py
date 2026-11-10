import json

from dojo_checks import assert_image, docker


def test_no_build_junk_in_image():
    size = assert_image("notes:2")["Size"]
    base = json.loads(docker("image", "inspect", "python:3.12-alpine"))[0]["Size"]
    assert size - base < 2_000_000, (
        f"notes:2 is {(size - base) / 1e6:.0f} MB bigger than python:3.12-alpine: the build cache "
        "is still in it. Copy only site/ into a fresh final stage."
    )


def test_build_script_not_shipped():
    found = docker(
        "run",
        "--rm",
        "notes:2",
        "sh",
        "-c",
        "find / -name build.py -not -path '/proc/*' 2>/dev/null | head -1",
    )
    assert not found, f"build.py is in the final image ({found})"
