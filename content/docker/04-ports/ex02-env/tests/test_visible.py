from dojo_checks import http_get


def test_both_greetings():
    assert "Hello from Docker!" in http_get("http://docker:8081", wait=10)[1]
    assert "Hola from Docker!" in http_get("http://docker:8082", wait=10)[1]
