from hoss_checks import assert_rolled_out, http_get


def test_shop_answers():
    assert_rolled_out("shop")
    status, body = http_get("http://k3s:30085", wait=20)
    assert status == 200 and body.startswith("Shop from shop-"), (
        f"http://k3s:30085 gave {status}: {body[:80]!r}"
    )
