from dojo_checks import k8s


def test_cronjob():
    spec = k8s("cronjob", "report")["spec"]
    assert spec["schedule"] == "*/5 * * * *", f"the schedule is {spec['schedule']!r}"
    assert spec.get("concurrencyPolicy") == "Forbid"
    assert spec.get("successfulJobsHistoryLimit") == 2
