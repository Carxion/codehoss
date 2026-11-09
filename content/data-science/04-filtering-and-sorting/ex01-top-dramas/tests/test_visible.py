def test_columns(run_program):
    got = run_program().vars.get("top_dramas")
    assert list(got.columns) == ["title", "year", "rating"], f"columns are {list(got.columns)}"
