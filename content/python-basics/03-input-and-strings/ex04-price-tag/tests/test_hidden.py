def test_small_numbers_still_show_two_decimals(run_program):
    got = run_program(["pen", "2", "5"]).lines[3:]
    assert got == ["PEN", "Price: $2.00", "Total: $10.00"], f"Got {got}"


def test_big_totals_get_separators(run_program):
    got = run_program(["tv", "999.99", "1200"]).last_line
    assert got == "Total: $1,199,988.00", f"Expected 'Total: $1,199,988.00', got {got!r}"
