import time

from hoss_checks import assert_rolled_out, k8s_list, kubectl, wait_until


def test_data_survives_a_new_pod():
    assert_rolled_out("notes", timeout=120)
    kubectl("exec", "deploy/notes", "--", "sh", "-c", "echo proof-123 > /data/proof.txt")
    old = {p["metadata"]["name"] for p in k8s_list("pods", selector="app=notes")}
    kubectl("delete", "pod", "-l", "app=notes", "--wait=true", timeout=90)

    def fresh_and_ready():
        pods = k8s_list("pods", selector="app=notes")
        return [
            p
            for p in pods
            if p["metadata"]["name"] not in old and p["status"]["phase"] == "Running"
        ]

    wait_until(fresh_and_ready, timeout=90, message="no new notes pod came up")
    time.sleep(1)
    assert kubectl("exec", "deploy/notes", "--", "cat", "/data/proof.txt") == "proof-123", (
        "the file didn't survive: is the claim mounted at /data?"
    )
