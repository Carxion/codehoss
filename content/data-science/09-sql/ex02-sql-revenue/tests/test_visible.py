def test_shape(run_program):
    top = run_program().vars.get("top_customers")
    assert list(top.columns) == ["name", "revenue"], f"columns are {list(top.columns)}"
    assert len(top) == 5, f"Expected 5 rows, got {len(top)}"
