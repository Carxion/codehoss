import base64

from hoss_checks import k8s, kubectl


def test_secret_value():
    data = k8s("secret", "db-credentials")["data"]
    assert base64.b64decode(data["password"]).decode() == "s3cret", (
        "the key should be password, the value s3cret"
    )


def test_mounted_as_file():
    assert kubectl("exec", "deploy/app", "--", "cat", "/etc/secrets/password") == "s3cret"
