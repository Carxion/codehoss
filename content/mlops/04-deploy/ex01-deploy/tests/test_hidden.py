from hoss_checks import k8s


def test_spec():
    container = k8s("deployment", "house-api")["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "docker:5000/house-api:1.0.0", "deploy an exact version"
    assert container["readinessProbe"]["httpGet"]["path"] == "/health"
