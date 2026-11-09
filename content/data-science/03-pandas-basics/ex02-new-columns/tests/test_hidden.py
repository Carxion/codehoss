import pandas as pd

DF = pd.read_csv("/data/movies.csv")


def test_values(run_program):
    result = run_program()
    df = result.vars["df"]
    assert (df["runtime_hours"] == (DF["runtime"] / 60).round(2)).all(), "runtime_hours is wrong"
    assert (df["is_long"] == (DF["runtime"] > 120)).all(), "is_long is wrong"
    assert result.vars.get("long_count") == (DF["runtime"] > 120).sum()
