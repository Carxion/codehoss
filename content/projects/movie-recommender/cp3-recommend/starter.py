# %%
import numpy as np
import pandas as pd

movies = pd.read_csv("/data/movies.csv")


def build_features(movies):
    genres = pd.get_dummies(movies["genre"], dtype=int)
    scaled = movies[["rating", "year"]]
    scaled = (scaled - scaled.min()) / (scaled.max() - scaled.min())
    return pd.concat([genres, scaled], axis=1).set_index(movies["title"])


# %%
features = build_features(movies)
features.head()


def similarity(features, a, b):
    x, y = features.loc[a].to_numpy(dtype=float), features.loc[b].to_numpy(dtype=float)
    return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y)))


# %%
first, second = features.index[:2]
similarity(features, first, first), similarity(features, first, second)


def recommend(features, title, k=5):
    scores = []
    # TODO: for every other title, append (similarity, other_title)
    # TODO: sort best first, ties in title order, and return the first k titles
    return []


# %%
recommend(features, features.index[0])
