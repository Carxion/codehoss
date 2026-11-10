import json

from dojo_checks import http_get, inspect_container


def test_serves():
    inspect_container("house-api")
    status, body = http_get("http://docker:8080/health", wait=20)
    assert status == 200 and json.loads(body)["model_version"] == "1.0.0", body
