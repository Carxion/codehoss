from dojo_checks import k8s


def test_quota():
    hard = k8s("resourcequota", "team-quota", "sandbox")["spec"]["hard"]
    assert hard.get("pods") == "3", f"pods is {hard.get('pods')}"
    assert hard.get("requests.cpu") == "500m" and hard.get("requests.memory") == "256Mi", (
        f"hard is {hard}"
    )
