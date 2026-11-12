from hoss_checks import k8s_list


def test_nothing_in_default():
    names = [d["metadata"]["name"] for d in k8s_list("deployments")]
    assert "web" not in names, "web ended up in default too: kubectl delete deploy web -n default"
