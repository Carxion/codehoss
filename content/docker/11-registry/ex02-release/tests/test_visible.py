import json

from hoss_checks import http_get


def test_both_tags_pushed():
    status, body = http_get("http://docker:5000/v2/hello-app/tags/list", wait=5)
    assert status == 200, body
    tags = json.loads(body)["tags"]
    assert "1.1" in tags and "latest" in tags, f"the registry has tags {tags}"
