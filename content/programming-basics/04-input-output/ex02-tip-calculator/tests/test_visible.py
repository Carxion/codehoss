def test_forty(run_program):
    lines = run_program(["40", "15"]).lines
    assert lines[-2:] == ["Tip: 6", "Total: 46"], f"The last two lines were {lines[-2:]}"
