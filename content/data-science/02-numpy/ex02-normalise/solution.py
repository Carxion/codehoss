# %%
import numpy as np


def normalise(values):
    return (values - values.min()) / (values.max() - values.min())


normalise(np.array([10, 15, 20]))
