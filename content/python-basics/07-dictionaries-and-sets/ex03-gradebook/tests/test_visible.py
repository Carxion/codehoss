def test_example(run_program):
    got = run_program(["ana 80", "ben 65", "ana 90", ""]).lines[4:]
    assert got == ["ana: 2 scores, average 85.0", "ben: 1 scores, average 65.0"], f"Got {got}"
