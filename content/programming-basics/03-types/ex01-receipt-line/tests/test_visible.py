def test_notebook(run_program):
    result = run_program()
    assert result.vars.get("line") == "Notebook x4 = 12", f"line is {result.vars.get('line')!r}"
