from dojo_checks import k8s


def test_uses_registry_image():
    image = k8s("deployment", "hello")["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image == "docker:5000/hello-k8s:1"
