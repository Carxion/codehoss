import time

from dojo_checks import docker


def test_it_keeps_printing():
    before = len(docker("logs", "ticker").splitlines())
    time.sleep(2.5)
    after = len(docker("logs", "ticker").splitlines())
    assert after > before, "ticker's logs aren't growing: it should print the date every second"
