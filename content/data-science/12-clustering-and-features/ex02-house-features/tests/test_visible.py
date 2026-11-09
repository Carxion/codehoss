def test_columns(run_program):
    houses = run_program().vars["houses"]
    for column in ("price_per_sqft", "is_new"):
        assert column in houses.columns, f"Add the {column!r} column"
