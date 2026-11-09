import pandas as pd


def test_excludes_itself():
    from main import build_features, recommend

    features = build_features(pd.read_csv("/data/movies.csv"))
    title = features.index[0]
    got = recommend(features, title, k=5)
    assert len(got) == 5 and title not in got, got
