from hoss_checks import k8s


def test_greeting_not_hardcoded():
    container = k8s("deployment", "greeter")["spec"]["template"]["spec"]["containers"][0]
    assert not container.get("env"), "keep GREETING in the ConfigMap, not in the Deployment"
