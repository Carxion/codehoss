def test_2024(run_program):
    got = run_program(["2024"]).last_line
    assert got == "2024 is a leap year", f"Got {got!r}"
