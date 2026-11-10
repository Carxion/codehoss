from dojo_checks import assert_rolled_out, k8s


def test_three_ready():
    assert k8s("deployment", "web")["spec"]["replicas"] == 3, "set replicas: 3"
    assert_rolled_out("web")
