def test_first_line(run_program):
    got = run_program().lines[0]
    assert got == "Seconds in an hour: 3600", f"First line should be 'Seconds in an hour: 3600', got {got!r}"
