import json

from hoss_checks import k8s, kubectl, wait_until


def test_two_endpoints():
    def count():
        slices = json.loads(
            kubectl("get", "endpointslices", "-l", "kubernetes.io/service-name=web", "-o", "json")
        )["items"]
        return sum(len(s.get("endpoints") or []) for s in slices) >= 2

    wait_until(count, timeout=30, message="the Service should have both pods as endpoints")


def test_ports():
    port = k8s("service", "web")["spec"]["ports"][0]
    assert port["port"] == 80 and port.get("targetPort") == 8000
