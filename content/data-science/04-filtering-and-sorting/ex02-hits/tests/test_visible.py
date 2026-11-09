import pandas as pd

DF = pd.read_csv("/data/movies.csv")
HITS = DF[(DF["rating"] >= 7) & (DF["gross_millions"] >= 50)]


def test_hits(run_program):
    got = run_program().vars.get("hits")
    assert len(got) == len(HITS), f"hits has {len(got)} rows, expected {len(HITS)}"
