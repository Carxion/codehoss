import pandas as pd


def test_is_series(run_program):
    got = run_program().vars.get("revenue_by_region")
    assert isinstance(got, pd.Series), "revenue_by_region should be a Series (use groupby)"
