from dojo_checks import assert_rolled_out, k8s


def test_probes_configured():
    container = k8s("deployment", "slow")["spec"]["template"]["spec"]["containers"][0]
    ready = container.get("readinessProbe") or {}
    assert ready.get("httpGet", {}).get("path") == "/ready", "the readinessProbe should GET /ready"
    assert "tcpSocket" in (container.get("livenessProbe") or {}), "add a tcpSocket livenessProbe"
    assert_rolled_out("slow", timeout=120)
