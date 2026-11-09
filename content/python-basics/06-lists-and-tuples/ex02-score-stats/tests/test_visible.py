def test_three_scores(run_program):
    lines = run_program(["3", "4", "9", "6"]).lines[-3:]
    assert lines == ["Highest: 9", "Lowest: 4", "Average: 6.3"], f"Got {lines}"
