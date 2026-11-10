def test_two_items(run_program):
    lines = run_program(["milk", "eggs", "done"]).lines
    assert lines[-3:] == ["You need 2 items:", "- milk", "- eggs"], (
        f"The end of the output was {lines[-3:]}"
    )
