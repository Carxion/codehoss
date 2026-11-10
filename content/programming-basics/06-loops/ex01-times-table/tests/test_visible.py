def test_seven(run_program):
    lines = run_program(["7"]).lines[1:]
    assert lines[:2] == ["7 x 1 = 7", "7 x 2 = 14"], f"The table starts {lines[:2]}"
    assert len(lines) == 10, f"There should be 10 lines in the table, not {len(lines)}"
