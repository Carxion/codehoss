from dojo_checks import http_get


def test_it_answers_from_outside():
    status, body = http_get("http://docker:8086", wait=10)
    assert status == 200 and "Now you can hear me" in body
