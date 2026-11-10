from dojo_checks import k8s, wait_until


def test_web_is_running():
    pod = k8s("pod", "web")
    assert pod["metadata"].get("labels", {}).get("app") == "web", "label the pod app: web"
    wait_until(
        lambda: k8s("pod", "web")["status"]["phase"] == "Running",
        timeout=60,
        message="web isn't Running: kubectl describe pod web shows why",
    )
