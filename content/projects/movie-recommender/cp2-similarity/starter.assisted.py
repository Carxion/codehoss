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
    """Cosine similarity of the rows for titles a and b."""
    raise NotImplementedError


# %%
first, second = features.index[:2]
similarity(features, first, first), similarity(features, first, second)
