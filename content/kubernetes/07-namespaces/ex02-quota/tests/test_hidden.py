from dojo_checks import k8s, k8s_list, wait_until


def test_only_three_pods():
    k8s("deployment", "busy", "sandbox")
    running = wait_until(
        lambda: (
            len([p for p in k8s_list("pods", "sandbox") if p["status"]["phase"] == "Running"]) == 3
        ),
        timeout=90,
        message="expected 3 running busy pods in sandbox (the quota allows 3 of the 5)",
    )
    assert running
    assert k8s("resourcequota", "team-quota", "sandbox")["status"]["used"]["pods"] == "3"
