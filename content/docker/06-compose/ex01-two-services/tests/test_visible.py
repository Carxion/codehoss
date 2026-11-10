from dojo_checks import http_get


def test_web_shows_fruit():
    status, body = http_get("http://docker:8090", wait=15)
    assert status == 200, body
    assert "apple, banana, cherry" in body
