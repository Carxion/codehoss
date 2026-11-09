# %%
import numpy as np
import pandas as pd

movies = pd.read_csv("/data/movies.csv")


def build_features(movies):
    genres = pd.get_dummies(movies["genre"], dtype=int)
    scaled = movies[["rating", "year"]]
    # TODO: rescale each column of scaled to 0..1
    # TODO: put genres and scaled side by side and index by title
    return genres


# %%
features = build_features(movies)
features.head()
