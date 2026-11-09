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
