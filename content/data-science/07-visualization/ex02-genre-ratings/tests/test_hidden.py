import pandas as pd
from hoss_checks import assert_series_matches, first_axes

DF = pd.read_csv("/data/movies.csv")
EXPECTED = DF.groupby("genre")["rating"].mean().sort_values(ascending=False)


def test_avg(run_program):
    assert_series_matches(run_program().vars.get("avg_by_genre"), EXPECTED, name="avg_by_genre")


def test_chart(run_program):
    run_program()
    ax = first_axes()
    assert ax["bars"] == len(EXPECTED), (
        f"Expected one bar per genre ({len(EXPECTED)}), found {ax['bars']}"
    )
    assert ax["title"], "Add a title"
    assert ax["ylabel"] == "Average rating", f"The y label is {ax['ylabel']!r}"
