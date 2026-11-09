import pandas as pd


def test_cp1_values():
    from main import build_features

    movies = pd.read_csv("/data/movies.csv")
    features = build_features(movies)
    genres = sorted(movies["genre"].unique())
    assert list(features.columns) == genres + ["rating", "year"], list(features.columns)
    assert features["rating"].min() == 0 and features["rating"].max() == 1
    first = movies.iloc[0]
    assert features.loc[first["title"], first["genre"]] == 1
