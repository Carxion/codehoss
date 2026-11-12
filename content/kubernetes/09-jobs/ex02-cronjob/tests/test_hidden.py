from hoss_checks import k8s, kubectl, wait_until


def test_ran_it_now():
    job = k8s("job", "report-now")
    owners = job["metadata"].get("annotations", {})
    assert owners.get("cronjob.kubernetes.io/instantiate") == "manual", (
        "make report-now with --from=cronjob/report"
    )
    wait_until(
        lambda: k8s("job", "report-now")["status"].get("succeeded"),
        timeout=90,
        message="report-now hasn't finished",
    )
    assert kubectl("logs", "job/report-now") == "report done"
