def test_columns(run_program):
    denver = run_program().vars.get("denver")
    assert list(denver.columns) == ["name", "joined"], f"columns are {list(denver.columns)}"
