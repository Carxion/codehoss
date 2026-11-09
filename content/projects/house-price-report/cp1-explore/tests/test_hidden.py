import pandas as pd

FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]


def test_cp1_facts():
    from main import explore

    df = pd.read_csv("/data/houses.csv")
    got = explore(df)
    assert got["price_mean"] == round(df["price"].mean())
    assert got["price_median"] == round(df["price"].median())
    assert got["strongest_feature"] == df[FEATURES].corrwith(df["price"]).abs().idxmax()
