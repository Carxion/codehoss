def test_warm_days(run_program):
    result = run_program()
    assert result.vars.get("warm_days") == [22, 25, 21], (
        f"warm_days is {result.vars.get('warm_days')}"
    )
    assert result.last_line == "3 warm days: [22, 25, 21]"
