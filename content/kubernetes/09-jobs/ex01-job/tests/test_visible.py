from hoss_checks import k8s, kubectl, wait_until


def test_completed_three_times():
    k8s("job", "squares")
    wait_until(
        lambda: k8s("job", "squares")["status"].get("succeeded") == 3,
        timeout=120,
        message="squares hasn't completed 3 times: kubectl get job squares",
    )
    assert kubectl("logs", "job/squares") == "338350"
