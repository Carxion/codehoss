from hoss_checks import k8s, kubectl, wait_until


def test_pod_finished():
    pod = k8s("pod", "hello")
    assert pod["spec"]["containers"][0]["image"] == "python:3.12-alpine"
    phase = wait_until(
        lambda: (
            k8s("pod", "hello")["status"]["phase"] in ("Succeeded", "Failed")
            and k8s("pod", "hello")["status"]["phase"]
        ),
        timeout=60,
        message="hello hasn't finished yet",
    )
    assert phase == "Succeeded", f"hello ended as {phase}: look at kubectl logs hello"


def test_logs():
    assert kubectl("logs", "hello") == "Hello from Kubernetes"
