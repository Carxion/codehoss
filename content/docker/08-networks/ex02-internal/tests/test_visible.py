import json

from dojo_checks import docker, inspect_container


def test_backend_is_internal():
    info = json.loads(docker("network", "inspect", "backend"))[0]
    assert info["Internal"], "backend should be created with --internal"


def test_vault_only_on_backend():
    networks = inspect_container("vault")["NetworkSettings"]["Networks"]
    assert list(networks) == ["backend"], f"vault should be on backend only, not {list(networks)}"
