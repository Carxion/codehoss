from dojo_checks import lab_dir, sh


def test_template_uses_values():
    out = sh(
        f"helm template demo {lab_dir()}/chart --set replicas=4 --set greeting=Yo", check=True
    ).stdout
    assert "replicas: 4" in out, "replicas isn't taken from .Values.replicas"
    assert "Yo" in out, "the greeting isn't taken from .Values.greeting"
