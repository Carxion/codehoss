from hoss_checks import assert_rolled_out, http_get, k8s


def test_app_reads_secret():
    k8s("secret", "db-credentials")
    assert_rolled_out("app")
    status, body = http_get("http://k3s:30082", wait=20)
    assert "password has 6 characters" in body, body
