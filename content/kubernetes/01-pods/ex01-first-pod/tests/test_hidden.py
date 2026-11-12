from hoss_checks import k8s


def test_does_not_restart():
    assert k8s("pod", "hello")["spec"]["restartPolicy"] == "Never", "use --restart=Never"
