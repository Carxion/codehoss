from dojo_checks import assert_rolled_out, http_get, k8s


def test_back_on_version_1():
    image = k8s("deployment", "shop")["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image == "docker:5000/shop:1", f"shop runs {image}; roll back to version 1"
    assert_rolled_out("shop")
    assert "Welcome to the shop" in http_get("http://k3s:30084", wait=20)[1]
