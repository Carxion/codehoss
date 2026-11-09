import numpy as np


def test_perfect_fit():
    from main import mse

    assert mse(2, 0, np.array([1.0, 2.0]), np.array([2.0, 4.0])) == 0
