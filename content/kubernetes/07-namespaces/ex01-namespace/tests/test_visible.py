from dojo_checks import assert_rolled_out, k8s


def test_namespace():
    ns = k8s("namespace", "shop", namespace=None)
    assert ns["metadata"].get("labels", {}).get("team") == "shop", "label the namespace team: shop"


def test_web_in_shop():
    assert_rolled_out("web", namespace="shop")
