from hoss_checks import assert_image, containers, docker


def test_counter_image_counts():
    assert_image("counter:1")
    out = docker("run", "--rm", "-v", "counts:/data", "counter:1")
    assert out.startswith("visit number ") and int(out.split()[-1]) >= 4


def test_used_rm():
    leftovers = [c for c in containers("ancestor=counter:1", all=True)]
    assert len(leftovers) == 0, "use --rm so each counter container is removed when it exits"
