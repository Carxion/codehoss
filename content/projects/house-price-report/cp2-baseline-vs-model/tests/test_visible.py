import pandas as pd

FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]


def test_model_beats_baseline():
    from main import evaluate

    got = evaluate(pd.read_csv("/data/houses.csv"), FEATURES)
    assert got["model_mae"] < got["baseline_mae"], got
