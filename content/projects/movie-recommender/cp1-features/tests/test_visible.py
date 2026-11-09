import pandas as pd


def test_index_and_columns():
    from main import build_features

    movies = pd.read_csv("/data/movies.csv")
    features = build_features(movies)
    assert list(features.index) == list(movies["title"]), "Index the rows by title"
    assert list(features.columns)[-2:] == ["rating", "year"]
