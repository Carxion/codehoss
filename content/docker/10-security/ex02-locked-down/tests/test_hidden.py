import time

from hoss_checks import docker, inspect_container, sh


def test_still_working():
    time.sleep(1.5)
    assert inspect_container("locked")["State"]["Running"], (
        "locked stopped: check docker logs locked"
    )
    first = docker("exec", "locked", "cat", "/tmp/heartbeat")
    time.sleep(1.5)
    assert docker("exec", "locked", "cat", "/tmp/heartbeat") != first


def test_cannot_write_elsewhere():
    assert sh("docker exec locked touch /app/oops").returncode != 0
