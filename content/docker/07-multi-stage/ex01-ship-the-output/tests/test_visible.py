from hoss_checks import http_get


def test_site_served():
    status, body = http_get("http://docker:8083", wait=10)
    assert status == 200 and "Field notes" in body and "volumes outlive containers" in body
