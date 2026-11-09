import pandas as pd
from dojo_checks import assert_close

DF = pd.read_csv("/data/movies.csv")


def test_mean(run_program):
    stats = run_program().vars.get("rating_stats")
    assert "mean" in stats, "rating_stats needs a 'mean' key"
    assert_close(stats["mean"], round(DF["rating"].mean(), 2), name="rating_stats['mean']")
