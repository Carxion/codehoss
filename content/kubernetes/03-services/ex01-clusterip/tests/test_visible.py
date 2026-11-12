from hoss_checks import assert_rolled_out, k8s, kubectl, wait_until


def test_service_reaches_pods():
    service = k8s("service", "web")
    assert service["spec"].get("selector") == {"app": "web"}, "select the pods with app: web"
    assert_rolled_out("web")
    out = wait_until(
        lambda: kubectl(
            "exec", "deploy/web", "--", "sh", "-c", "wget -qO- -T 3 http://web || true"
        ),
        timeout=30,
        message="nothing answered at http://web from inside the cluster",
    )
    assert "Hello from web-" in out
