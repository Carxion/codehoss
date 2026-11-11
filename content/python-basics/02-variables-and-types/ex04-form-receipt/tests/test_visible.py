def test_prints_the_receipt(run_program):
    got = run_program().last_line
    assert got == "3 x 4.25 = 12.75", f"Expected '3 x 4.25 = 12.75', got {got!r}"
