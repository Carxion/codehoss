import pandas as pd
from hoss_checks import assert_close

DF = pd.read_csv("/data/movies.csv")
HITS = DF[(DF["rating"] >= 7) & (DF["gross_millions"] >= 50)]


def test_rate(run_program):
    assert_close(run_program().vars.get("hit_rate"), round(len(HITS) / len(DF), 3), name="hit_rate")


def test_by_genre(run_program):
    got = run_program().vars.get("hits_by_genre")
    assert dict(got) == HITS["genre"].value_counts().to_dict(), f"hits_by_genre is {got}"
