from hoss_checks import assert_rolled_out, k8s


def test_resources():
    resources = (
        k8s("deployment", "limited")["spec"]["template"]["spec"]["containers"][0].get("resources")
        or {}
    )
    assert resources.get("requests") == {"cpu": "50m", "memory": "32Mi"}, (
        f"requests are {resources.get('requests')}"
    )
    assert resources.get("limits") == {"cpu": "200m", "memory": "64Mi"}, (
        f"limits are {resources.get('limits')}"
    )
    assert_rolled_out("limited")
