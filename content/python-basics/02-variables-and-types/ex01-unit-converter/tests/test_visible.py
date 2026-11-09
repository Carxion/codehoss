def test_miles_is_calculated(run_program):
    miles = run_program().vars.get("miles")
    assert miles == 6.21, f"miles should be 6.21 but was {miles!r}"
