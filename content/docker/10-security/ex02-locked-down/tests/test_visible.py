from hoss_checks import inspect_container


def test_locked_down():
    host = inspect_container("locked")["HostConfig"]
    assert host["ReadonlyRootfs"], "add --read-only"
    assert "ALL" in (host.get("CapDrop") or []), "add --cap-drop ALL"
    assert "/tmp" in (host.get("Tmpfs") or {}), "add --tmpfs /tmp"
