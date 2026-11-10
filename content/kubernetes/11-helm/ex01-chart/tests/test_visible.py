import json

from dojo_checks import assert_rolled_out, k8s, sh


def test_release_installed():
    releases = json.loads(sh("helm list -o json", check=True).stdout or "[]")
    shop = [r for r in releases if r["name"] == "shop"]
    assert shop, "no release called shop: helm install shop ./chart"
    assert shop[0]["status"] == "deployed", f"shop is {shop[0]['status']}"
    assert_rolled_out("shop")
    container = k8s("deployment", "shop")["spec"]["template"]["spec"]["containers"][0]
    assert k8s("deployment", "shop")["spec"]["replicas"] == 2, (
        "replicas should come from values.yaml (2)"
    )
    assert container["env"][0]["value"] == "Howdy", (
        "the greeting should come from values.yaml (Howdy)"
    )
