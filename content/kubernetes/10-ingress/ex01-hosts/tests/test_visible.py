from dojo_checks import assert_rolled_out, ingress_get, k8s


def test_shop():
    k8s("ingress", "sites")
    assert_rolled_out("shop")
    status, body = ingress_get("/", host="shop.local")
    assert status == 200 and body.startswith("Shop from shop-"), (
        f"shop.local gave {status}: {body[:80]!r}"
    )
