import numpy as np


def test_small_example():
    from main import baseline_accuracy

    assert baseline_accuracy(np.array([1, 1, 2]), np.array([1, 2, 1, 1])) == 0.75
