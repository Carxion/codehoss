import numpy as np


def test_learns_a_line():
    from main import train

    x = np.linspace(0, 2, 20)
    w, b = train(x, 3 * x - 2)
    assert abs(w - 3) < 0.05 and abs(b + 2) < 0.05, f"got w={w:.3f}, b={b:.3f}"
