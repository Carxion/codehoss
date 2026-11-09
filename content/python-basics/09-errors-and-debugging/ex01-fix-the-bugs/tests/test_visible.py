def test_average(run_program):
    lines = run_program().lines
    assert "Average: 4.0" in lines, f"Expected 'Average: 4.0' in {lines}"
