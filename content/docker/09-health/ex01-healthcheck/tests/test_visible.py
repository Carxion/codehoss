import time

from dojo_checks import inspect_container


def test_becomes_healthy():
    deadline = time.monotonic() + 25
    status = None
    while time.monotonic() < deadline:
        health = inspect_container("healthy")["State"].get("Health")
        assert health is not None, "healthy has no health check: add HEALTHCHECK to the Dockerfile and rebuild"
        status = health["Status"]
        if status == "healthy":
            return
        time.sleep(1)
    raise AssertionError(f"healthy is still '{status}' after 25s. Does the check fetch /health on port 8000?")
