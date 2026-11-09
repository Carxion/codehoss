import pandas as pd
from dojo_checks import assert_series_matches

SALES = pd.read_csv("/data/sales.csv")
SALES["revenue"] = SALES["units"] * SALES["unit_price"]
EXPECTED = SALES.groupby("region")["revenue"].sum().round(2).sort_values(ascending=False)


def test_values(run_program):
    assert_series_matches(
        run_program().vars.get("revenue_by_region"), EXPECTED, name="revenue_by_region"
    )


def test_best(run_program):
    assert run_program().vars.get("best_region") == EXPECTED.index[0]
