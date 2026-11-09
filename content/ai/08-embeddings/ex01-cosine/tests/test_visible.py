import numpy as np


def test_same_direction():
    from main import cosine

    assert abs(cosine(np.array([1.0, 2.0]), np.array([2.0, 4.0])) - 1) < 1e-9
