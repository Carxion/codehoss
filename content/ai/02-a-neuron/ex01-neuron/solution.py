# %%
import numpy as np


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def neuron(inputs, weights, bias):
    return sigmoid(np.dot(inputs, weights) + bias)


# %%
neuron(np.array([1, 0]), np.array([2, 2]), -1)
