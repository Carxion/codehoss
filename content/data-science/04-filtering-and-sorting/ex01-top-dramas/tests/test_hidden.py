import pandas as pd
from hoss_checks import assert_frame_matches

DF = pd.read_csv("/data/movies.csv")


def test_rows(run_program):
    expected = (
        DF[(DF["genre"] == "Drama") & (DF["year"] >= 2000)]
        .sort_values(["rating", "title"], ascending=[False, True])
        .head(5)[["title", "year", "rating"]]
    )
    assert_frame_matches(run_program().vars.get("top_dramas"), expected, name="top_dramas")
