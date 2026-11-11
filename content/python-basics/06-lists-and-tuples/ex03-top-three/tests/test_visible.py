def test_example(run_program):
    got = run_program(["70, 95, 88, 60, 91"]).lines[1:]
    assert got == ["Top 3: 95, 91, 88", "Lowest: 60", "80 or more: 3"], f"Got {got}"
