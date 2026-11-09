import numpy as np


def test_unsorted_and_negative():
    from main import normalise

    got = normalise(np.array([-5.0, 5.0, 0.0, 15.0]))
    assert np.allclose(got, [0, 0.5, 0.25, 1]), f"got {got}"
