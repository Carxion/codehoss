import math

import numpy as np


def test_neuron():
    from main import neuron, sigmoid

    assert abs(sigmoid(2) - 1 / (1 + math.exp(-2))) < 1e-9
    got = neuron(np.array([1, 0]), np.array([2, 2]), -1)
    assert abs(got - 1 / (1 + math.exp(-1))) < 1e-9, f"neuron gave {got}"
    got = neuron(np.array([0.5, -1.0, 2.0]), np.array([1.0, 0.5, -0.25]), 0.2)
    assert abs(got - 1 / (1 + math.exp(-(0.5 - 0.5 - 0.5 + 0.2)))) < 1e-9
