from dojo_checks import k8s_list


def test_burstable():
    pods = k8s_list("pods", selector="app=limited")
    assert pods and all(p["status"].get("qosClass") == "Burstable" for p in pods)
