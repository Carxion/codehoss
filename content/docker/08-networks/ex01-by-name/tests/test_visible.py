from dojo_checks import http_get


def test_app_reaches_db():
    status, body = http_get("http://docker:8084", wait=10)
    assert status == 200, body
    assert "The answer is 42" in body
