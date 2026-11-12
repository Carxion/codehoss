from hoss_checks import assert_rolled_out, k8s


def test_updated_to_hola():
    env = k8s("deployment", "greeter")["spec"]["template"]["spec"]["containers"][0]["env"]
    assert {"name": "GREETING", "value": "Hola"} in env, "set GREETING to Hola and apply again"
    assert_rolled_out("greeter")
