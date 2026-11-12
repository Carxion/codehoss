from hoss_checks import assert_rolled_out, ingress_get


def test_blog():
    assert_rolled_out("blog")
    status, body = ingress_get("/", host="blog.local")
    assert status == 200 and body.startswith("Blog from blog-"), (
        f"blog.local gave {status}: {body[:80]!r}"
    )


def test_unknown_host():
    status, _ = ingress_get("/", host="nope.local", wait=5)
    assert status == 404, "only shop.local and blog.local should be routed"
