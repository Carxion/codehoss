from hoss_checks import k8s


def test_timings():
    container = k8s("deployment", "slow")["spec"]["template"]["spec"]["containers"][0]
    assert container["readinessProbe"].get("periodSeconds") == 2
    assert container["livenessProbe"].get("initialDelaySeconds", 0) >= 10, (
        "give the app time before liveness checks"
    )
