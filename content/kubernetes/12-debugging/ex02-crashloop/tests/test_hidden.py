from hoss_checks import k8s


def test_config_unchanged_and_probe_fixed():
    assert k8s("configmap", "worker-config")["data"] == {"mode": "production"}, (
        "fix the Deployment, not the ConfigMap"
    )
    container = k8s("deployment", "worker")["spec"]["template"]["spec"]["containers"][0]
    assert container["readinessProbe"]["tcpSocket"]["port"] == 8000
