import time

from hoss_checks import inspect_container


def test_it_was_restarted():
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if inspect_container("flaky")["RestartCount"] >= 1:
            return
        time.sleep(1)
    raise AssertionError("Docker hasn't restarted flaky yet")
