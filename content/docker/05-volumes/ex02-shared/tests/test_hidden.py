import time

from dojo_checks import docker


def test_another_container_sees_updates():
    read = ["run", "--rm", "-v", "shared:/shared", "alpine:3.22", "cat", "/shared/now.txt"]
    first = docker(*read)
    time.sleep(2.2)
    assert docker(*read) != first, "now.txt isn't changing: is writer's loop running?"
