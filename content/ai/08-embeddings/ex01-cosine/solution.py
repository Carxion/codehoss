# %%
import numpy as np


def cosine(a, b):
    lengths = np.linalg.norm(a) * np.linalg.norm(b)
    if lengths == 0:
        return 0.0
    return float(np.dot(a, b) / lengths)


# %%
cosine(np.array([1.0, 0.0]), np.array([1.0, 1.0]))
