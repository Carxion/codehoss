import numpy as np


def test_values():
    from main import mse

    x = np.array([1.0, 2.0, 3.0])
    y = np.array([2.0, 4.0, 6.0])
    assert abs(mse(1, 0, x, y) - (1 + 4 + 9) / 3) < 1e-9
    assert abs(mse(2, 1, x, y) - 1) < 1e-9
