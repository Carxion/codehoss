import json

from dojo_checks import assert_rolled_out, k8s, sh


def test_revision_3_had_three_replicas():
    values = json.loads(sh("helm get values blog --revision 3 -o json", check=True).stdout)
    assert values == {"greeting": "Hi", "replicas": 3}, f"revision 3 was set with {values}"


def test_current_state():
    assert_rolled_out("blog")
    deployment = k8s("deployment", "blog")
    assert deployment["spec"]["replicas"] == 1
    assert deployment["spec"]["template"]["spec"]["containers"][0]["env"][0]["value"] == "Hi"
