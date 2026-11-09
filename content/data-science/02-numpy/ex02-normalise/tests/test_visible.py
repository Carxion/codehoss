import numpy as np


def test_simple():
    from main import normalise

    assert np.allclose(normalise(np.array([10, 15, 20])), [0, 0.5, 1])
