from hoss_checks import http_get


def test_reachable_on_8080():
    status, body = http_get("http://docker:8080", wait=10)
    assert status == 200 and "Hello from Docker!" in body
