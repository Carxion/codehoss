# %%
import numpy as np
import pandas as pd

movies = pd.read_csv("/data/movies.csv")


def build_features(movies):
    """Genre one-hot columns + rating & year scaled to 0..1, indexed by title."""
    raise NotImplementedError


# %%
features = build_features(movies)
features.head()
