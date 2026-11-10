def test_135(run_program):
    got = run_program().last_line
    assert got == "135 minutes is 2 hours and 15 minutes", f"Your program showed {got!r}"
