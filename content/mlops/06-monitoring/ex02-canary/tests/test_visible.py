import json
import urllib.request

from dojo_checks import assert_rolled_out, ingress_get


def predict_through_ingress(values):
    request = urllib.request.Request(
        "http://k3s/predict",
        data=json.dumps(values).encode(),
        headers={"Host": "api.local"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as r:
        return json.load(r)


def health_version():
    status, body = ingress_get("/health", host="api.local", wait=90)
    assert status == 200, f"http://k3s/health (Host: api.local) gave {status}: {body[:120]}"
    return json.loads(body)["model_version"]


def settled_versions(expected, timeout=90):
    """Ask /health in batches until exactly the `expected` versions answer: the ingress
    controller takes a few seconds to notice pods that just became ready or went away."""
    import time

    deadline = time.monotonic() + timeout
    while True:
        seen = {health_version() for _ in range(16)}
        if seen == set(expected) or time.monotonic() > deadline:
            assert seen == set(expected), f"{sorted(seen)} answered, expected {sorted(expected)}"
            return seen
        time.sleep(2)


def test_both_versions_serve():
    assert_rolled_out("house-api", timeout=120)
    assert_rolled_out("house-api-canary", timeout=120)
    settled_versions({"1.0.0", "1.1.0"})
