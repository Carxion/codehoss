import pandas as pd
from dojo_checks import assert_close


def expected():
    df = pd.read_csv("/data/survey_messy.csv").drop_duplicates().copy()
    df["city"] = df["city"].str.strip().str.title()
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["satisfaction"] = pd.to_numeric(df["satisfaction"], errors="coerce")
    return df


def test_median(run_program):
    assert_close(
        run_program().vars.get("median_age"), expected()["age"].median(), name="median_age"
    )


def test_by_city(run_program):
    got = run_program().vars.get("satisfaction_by_city")
    want = expected().groupby("city")["satisfaction"].mean().round(2).to_dict()
    assert got.keys() == want.keys(), f"cities are {sorted(got)}"
    for city, value in want.items():
        assert_close(got[city], value, name=f"satisfaction_by_city[{city!r}]")
