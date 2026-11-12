from hoss_checks import k8s


def test_is_nodeport():
    spec = k8s("service", "web-public")["spec"]
    assert spec["type"] == "NodePort" and spec["ports"][0]["nodePort"] == 30080
