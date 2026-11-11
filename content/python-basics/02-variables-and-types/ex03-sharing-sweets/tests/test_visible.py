def test_47_sweets_6_children(run_program):
    got = run_program().lines
    assert got == ["Each child gets 7 sweets", "Left over: 5"], f"Got {got}"
