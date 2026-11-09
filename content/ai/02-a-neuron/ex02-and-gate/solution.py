# %%
import numpy as np


def neuron(inputs, weights, bias):
    return 1 / (1 + np.exp(-(np.dot(inputs, weights) + bias)))


weights = np.array([1.0, 1.0])
bias = -1.5

# %%
for x in ([0, 0], [0, 1], [1, 0], [1, 1]):
    print(x, round(float(neuron(np.array(x), weights, bias)), 3))
