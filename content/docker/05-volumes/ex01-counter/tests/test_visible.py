from hoss_checks import docker, sh


def test_volume_has_three_visits():
    assert sh("docker volume inspect counts").returncode == 0, (
        "create the volume: docker volume create counts"
    )
    visits = docker(
        "run", "--rm", "-v", "counts:/data", "alpine:3.22", "cat", "/data/visits.txt"
    ).splitlines()
    assert len(visits) >= 3, (
        f"the volume has {len(visits)} visit(s); run the counter 3 times with -v counts:/data"
    )
