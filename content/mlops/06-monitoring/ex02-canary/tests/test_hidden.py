from dojo_checks import k8s


def test_canary_spec():
    canary = k8s("deployment", "house-api-canary")["spec"]
    assert canary["replicas"] == 1
    assert canary["selector"]["matchLabels"] == {"app": "house-api", "track": "canary"}
    assert canary["template"]["spec"]["containers"][0]["image"] == "docker:5000/house-api:1.1.0"
    assert k8s("service", "house-api")["spec"]["selector"] == {"app": "house-api"}, (
        "leave the Service selecting app: house-api"
    )
