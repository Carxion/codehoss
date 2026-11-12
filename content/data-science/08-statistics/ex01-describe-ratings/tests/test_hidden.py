import pandas as pd
from hoss_checks import assert_close

DF = pd.read_csv("/data/movies.csv")


def test_all_stats(run_program):
    stats = run_program().vars.get("rating_stats")
    for key, value in [("median", DF["rating"].median()), ("std", DF["rating"].std())]:
        assert key in stats, f"rating_stats needs a {key!r} key"
        assert_close(stats[key], round(value, 2), name=f"rating_stats[{key!r}]")


def test_corr(run_program):
    expected = round(DF["votes"].corr(DF["gross_millions"]), 3)
    assert_close(run_program().vars.get("votes_gross_corr"), expected, name="votes_gross_corr")
