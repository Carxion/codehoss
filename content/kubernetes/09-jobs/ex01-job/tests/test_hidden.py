from dojo_checks import k8s


def test_spec():
    spec = k8s("job", "squares")["spec"]
    assert (spec.get("completions"), spec.get("parallelism"), spec.get("backoffLimit")) == (
        3,
        3,
        2,
    ), spec
