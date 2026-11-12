from hoss_checks import assert_rolled_out, http_get


def test_reachable_from_outside():
    assert_rolled_out("web")
    status, body = http_get("http://k3s:30080", wait=20)
    assert status == 200 and "Hello from web-" in body
