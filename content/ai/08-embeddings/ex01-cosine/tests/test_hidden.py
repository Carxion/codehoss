import math

import numpy as np


def test_values():
    from main import cosine

    assert abs(cosine(np.array([1.0, 0.0]), np.array([0.0, 3.0]))) < 1e-9
    assert abs(cosine(np.array([1.0, 0.0]), np.array([1.0, 1.0])) - 1 / math.sqrt(2)) < 1e-9
    assert abs(cosine(np.array([1.0, 0.0]), np.array([-2.0, 0.0])) + 1) < 1e-9
    assert cosine(np.array([0.0, 0.0]), np.array([1.0, 1.0])) == 0.0
