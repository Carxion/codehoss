from dojo_checks import assert_rolled_out, http_get, k8s


def test_bonjour():
    assert k8s("configmap", "greeter-config").get("data", {}).get("GREETING") == "Bonjour"
    assert_rolled_out("greeter")
    status, body = http_get("http://k3s:30081", wait=20)
    assert "Bonjour from greeter-" in body, body
