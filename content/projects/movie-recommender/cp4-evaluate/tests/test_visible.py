import pandas as pd


def test_range():
    from main import build_features, genre_precision

    movies = pd.read_csv("/data/movies.csv")
    got = genre_precision(movies, build_features(movies), k=3)
    assert 0 <= got <= 1, got
