from hoss_checks import k8s_list, kubectl, wait_until


def test_heals_itself():
    pods = k8s_list("pods", selector="app=web")
    victim = pods[0]["metadata"]["name"]
    kubectl("delete", "pod", victim, "--now")

    def healed():
        ready = [
            p
            for p in k8s_list("pods", selector="app=web")
            if p["metadata"]["name"] != victim and p["status"].get("phase") == "Running"
        ]
        return len(ready) >= 3

    wait_until(healed, timeout=60, message="the deleted pod wasn't replaced")
