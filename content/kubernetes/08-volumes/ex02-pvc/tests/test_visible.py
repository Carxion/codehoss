from dojo_checks import assert_rolled_out, k8s


def test_claim_bound():
    assert_rolled_out("notes", timeout=120)
    pvc = k8s("pvc", "notes-data")
    assert pvc["status"].get("phase") == "Bound", (
        "notes-data isn't Bound: kubectl describe pvc notes-data"
    )
    assert pvc["spec"]["resources"]["requests"]["storage"] == "50Mi"
