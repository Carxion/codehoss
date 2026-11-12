from hoss_checks import assert_rolled_out, ingress_get, k8s


def test_api_path():
    k8s("ingress", "app")
    assert_rolled_out("api")
    status, body = ingress_get("/api/", host="app.local")
    assert status == 200 and body.startswith("API from api-"), f"/api/ gave {status}: {body[:80]!r}"
