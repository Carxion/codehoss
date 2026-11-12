from hoss_checks import inspect_container


def test_both_on_appnet():
    for name in ("db", "app"):
        networks = inspect_container(name)["NetworkSettings"]["Networks"]
        assert "appnet" in networks, f"{name} isn't on appnet (it's on {', '.join(networks)})"


def test_db_not_published():
    ports = inspect_container("db")["HostConfig"]["PortBindings"] or {}
    assert not ports, "don't publish db's port: app reaches it over appnet"
