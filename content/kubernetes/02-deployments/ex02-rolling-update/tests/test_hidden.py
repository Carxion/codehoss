from hoss_checks import k8s, k8s_list, kubectl


def test_was_a_rollout_not_a_fresh_create():
    revision = int(
        k8s("deployment", "greeter")["metadata"]["annotations"]["deployment.kubernetes.io/revision"]
    )
    assert revision >= 2, "apply the original first, then the change, so it's a rolling update"


def test_pods_say_hola():
    pod = k8s_list("pods", selector="app=greeter")[0]["metadata"]["name"]
    assert kubectl("exec", pod, "--", "cat", "index.html").startswith("Hola from")
