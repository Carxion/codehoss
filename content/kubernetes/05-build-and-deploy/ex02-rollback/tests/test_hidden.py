from dojo_checks import k8s


def test_version_2_was_released_then_undone():
    revision = int(
        k8s("deployment", "shop")["metadata"]["annotations"]["deployment.kubernetes.io/revision"]
    )
    assert revision >= 3, (
        "release version 2 first (kubectl set image), then roll back with kubectl rollout undo"
    )
