import pandas as pd


def test_self_similarity():
    from main import build_features, similarity

    features = build_features(pd.read_csv("/data/movies.csv"))
    title = features.index[0]
    assert abs(similarity(features, title, title) - 1) < 1e-9
