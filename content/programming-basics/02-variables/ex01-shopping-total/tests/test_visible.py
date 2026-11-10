def test_total(run_program):
    result = run_program()
    assert result.vars.get("total") == 12, "total should be price * quantity (4 * 3 = 12)"
    assert result.last_line == "Total: 12", f"Your program showed {result.last_line!r}"
