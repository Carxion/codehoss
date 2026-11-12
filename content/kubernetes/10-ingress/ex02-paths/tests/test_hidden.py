from hoss_checks import assert_rolled_out, ingress_get


def test_everything_else_is_web():
    assert_rolled_out("web")
    for path in ("/", "/index.html"):
        status, body = ingress_get(path, host="app.local")
        assert status == 200 and body.startswith("Web from web-"), (
            f"{path} gave {status}: {body[:80]!r}"
        )
