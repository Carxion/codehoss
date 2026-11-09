# %%
import numpy as np


def train(x, y, lr=0.05, steps=1000):
    w, b = 0.0, 0.0
    for _ in range(steps):
        error = (w * x + b) - y
        w -= lr * 2 * (error * x).mean()
        b -= lr * 2 * error.mean()
    return w, b


# %%
x = np.linspace(0, 2, 20)
train(x, 3 * x - 2)
