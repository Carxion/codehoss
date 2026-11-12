from hoss_checks import k8s, kubectl


def test_serves_on_8000():
    out = kubectl("exec", "web", "--", "wget", "-qO-", "-T", "5", "http://127.0.0.1:8000")
    assert "Directory listing" in out


def test_declares_port():
    ports = k8s("pod", "web")["spec"]["containers"][0].get("ports") or []
    assert any(p.get("containerPort") == 8000 for p in ports), "declare containerPort: 8000"
