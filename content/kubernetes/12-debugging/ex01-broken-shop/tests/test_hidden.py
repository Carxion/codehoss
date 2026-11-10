from dojo_checks import k8s


def test_fixed_in_the_files():
    container = k8s("deployment", "shop")["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "python:3.12-alpine"
    svc = k8s("service", "shop")["spec"]
    assert svc["selector"] == {"app": "shop"}
    assert svc["ports"][0]["targetPort"] == 8000
