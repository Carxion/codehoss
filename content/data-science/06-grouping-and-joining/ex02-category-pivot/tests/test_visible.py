import pandas as pd


def test_pivot_shape(run_program):
    pivot = run_program().vars.get("pivot")
    assert isinstance(pivot, pd.DataFrame), "pivot should be a DataFrame (use pivot_table)"
    assert sorted(pivot.columns) == ["Bags", "Home", "Stationery"], (
        f"columns are {list(pivot.columns)}"
    )
