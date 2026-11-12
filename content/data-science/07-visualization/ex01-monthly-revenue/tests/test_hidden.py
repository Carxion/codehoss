import pandas as pd
from hoss_checks import assert_series_matches, first_axes

SALES = pd.read_csv("/data/sales.csv")
SALES["revenue"] = SALES["units"] * SALES["unit_price"]
SALES["month"] = pd.to_datetime(SALES["date"]).dt.month
EXPECTED = SALES.groupby("month")["revenue"].sum()


def test_monthly(run_program):
    assert_series_matches(run_program().vars.get("monthly"), EXPECTED, name="monthly")


def test_labels(run_program):
    run_program()
    ax = first_axes()
    assert (ax["xlabel"], ax["ylabel"]) == ("Month", "Revenue"), (
        f"labels are {ax['xlabel']!r}, {ax['ylabel']!r}"
    )
