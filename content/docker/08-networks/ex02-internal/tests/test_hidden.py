from dojo_checks import docker, inspect_container


def test_reachable_from_backend():
    out = docker("run", "--rm", "--network", "backend", "alpine:3.22", "wget", "-qO-", "-T", "5", "http://vault:6000")
    assert '"answer": 42' in out


def test_no_published_ports():
    assert not (inspect_container("vault")["HostConfig"]["PortBindings"] or {})
