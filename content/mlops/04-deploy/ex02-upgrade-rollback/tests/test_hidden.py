from hoss_checks import k8s_list


def test_1_1_0_was_rolled_out_first():
    images = {
        rs["spec"]["template"]["spec"]["containers"][0]["image"]
        for rs in k8s_list("replicasets", selector="app=house-api")
    }
    assert "docker:5000/house-api:1.1.0" in images, (
        "upgrade to 1.1.0 with kubectl set image before rolling back"
    )
