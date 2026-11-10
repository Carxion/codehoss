from dojo_checks import assert_rolled_out, http_get


def test_my_image_serves():
    assert_rolled_out("hello")
    status, body = http_get("http://k3s:30083", wait=20)
    assert "Hello from my own image" in body
