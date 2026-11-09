import pandas as pd
from dojo_checks import assert_close

DF = pd.read_csv("/data/ab_test.csv")


def test_rates(run_program):
    v = run_program().vars
    assert_close(
        v.get("rate_a"), round(DF[DF["group"] == "A"]["converted"].mean(), 4), name="rate_a"
    )
    assert_close(
        v.get("rate_b"), round(DF[DF["group"] == "B"]["converted"].mean(), 4), name="rate_b"
    )
