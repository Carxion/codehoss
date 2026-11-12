import json

from hoss_checks import http_get


def test_registry_has_the_image():
    status, body = http_get("http://docker:5000/v2/hello-app/tags/list", wait=5)
    assert status == 200, (
        "the registry doesn't know hello-app yet: tag it localhost:5000/hello-app:1.0 and push"
    )
    assert "1.0" in json.loads(body)["tags"]
