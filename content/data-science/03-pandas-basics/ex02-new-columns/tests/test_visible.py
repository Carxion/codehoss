def test_columns_exist(run_program):
    df = run_program().vars["df"]
    for column in ("runtime_hours", "is_long"):
        assert column in df.columns, f"df is missing the column {column!r}"
