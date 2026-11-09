def test_prints_sentence(run_program):
    got = run_program().last_line
    assert got == "10 km is 6.21 miles", (
        f"Last line should be '10 km is 6.21 miles' but was {got!r}"
    )


def test_miles_is_a_rounded_float(run_program):
    miles = run_program().vars.get("miles")
    assert isinstance(miles, float) and miles == 6.21, (
        f"miles should be the float 6.21, got {miles!r}"
    )
