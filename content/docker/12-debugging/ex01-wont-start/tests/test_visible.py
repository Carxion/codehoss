from dojo_checks import http_get


def test_it_answers():
    status, body = http_get("http://docker:8085", wait=10)
    assert status == 200 and "Fixed it!" in body
