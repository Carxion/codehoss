def test_full_output(run_program):
    lines = run_program().lines
    assert lines == ["Average: 4.0", "Highest: 7"], f"Got {lines}"
