import numpy as np
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


def test_cp2_value():
    from main import build_features, similarity

    features = build_features(pd.read_csv("/data/movies.csv"))
    a, b = features.index[3], features.index[10]
    x, y = features.loc[a].to_numpy(dtype=float), features.loc[b].to_numpy(dtype=float)
    expected = np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))
    assert abs(similarity(features, a, b) - expected) < 1e-9


def expected_recommend(features, title, k):
    from main import similarity

    scores = [(similarity(features, title, o), o) for o in features.index if o != title]
    scores.sort(key=lambda p: (-p[0], p[1]))
    return [o for _, o in scores[:k]]


def test_cp3_order():
    from main import build_features, recommend

    features = build_features(pd.read_csv("/data/movies.csv"))
    for title in features.index[:5]:
        assert recommend(features, title, k=4) == expected_recommend(features, title, 4)


def test_cp4_value():
    from main import build_features, genre_precision

    movies = pd.read_csv("/data/movies.csv")
    features = build_features(movies)
    genre_of = dict(zip(movies["title"], movies["genre"]))
    fractions = [
        sum(genre_of[r] == genre_of[t] for r in expected_recommend(features, t, 3)) / 3
        for t in features.index
    ]
    assert genre_precision(movies, features, k=3) == round(sum(fractions) / len(fractions), 3)
