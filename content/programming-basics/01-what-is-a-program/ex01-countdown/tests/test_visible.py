def test_countdown(run_program):
    lines = run_program().lines
    assert lines == ["3", "2", "1", "Lift off!"], f"Your program showed {lines}"
