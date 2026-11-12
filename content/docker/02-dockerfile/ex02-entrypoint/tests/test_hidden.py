from hoss_checks import assert_image


def test_entrypoint_and_cmd():
    config = assert_image("greet:2")["Config"]
    assert config.get("Entrypoint"), "use ENTRYPOINT for the part that always runs"
    assert config.get("Cmd") == ["world"], (
        f'CMD should be the default name, ["world"]; it is {config.get("Cmd")}'
    )
