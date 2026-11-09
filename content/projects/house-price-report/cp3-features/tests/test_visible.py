import pandas as pd


def test_columns():
    from main import add_features

    df = add_features(pd.read_csv("/data/houses.csv"))
    assert {"is_new", "size_per_bedroom"} <= set(df.columns)
