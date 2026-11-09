def test_prints_both_lines_exactly(run_program):
    lines = run_program().lines
    expected = ["Hello, world!", "I am learning Python."]
    assert lines == expected, f"Expected exactly {expected} but got {lines}"
