from dojo_checks import assert_image


def test_interval_is_short():
    check = assert_image("health:1")["Config"].get("Healthcheck") or {}
    assert check.get("Test"), "add a HEALTHCHECK"
    assert check.get("Interval", 0) <= 5_000_000_000, "check every 2 seconds (--interval=2s)"
    assert "/health" in " ".join(check["Test"])
