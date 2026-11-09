# %%
import numpy as np


def mse(w, b, x, y):
    predictions = w * x + b
    return ((predictions - y) ** 2).mean()


# %%
x = np.array([1.0, 2.0, 3.0])
y = np.array([2.0, 4.0, 6.0])
mse(2, 0, x, y), mse(1, 0, x, y)
