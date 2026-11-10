def test_average(run_program):
    result = run_program()
    assert result.vars.get("average") == 8.3, (
        f"average is {result.vars.get('average')}, but (7 + 8 + 10) / 3 rounded is 8.3"
    )
    assert result.last_line == "Average: 8.3"
