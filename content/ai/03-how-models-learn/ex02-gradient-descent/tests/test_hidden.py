import numpy as np


def test_exact_steps():
    from main import train

    x = np.array([1.0, 2.0])
    y = np.array([1.0, 2.0])
    w, b = train(x, y, lr=0.1, steps=1)
    # one step from w=b=0: error = -y
    assert abs(w - 0.1 * 2 * 2.5) < 1e-9 and abs(b - 0.1 * 2 * 1.5) < 1e-9, (
        f"after one step got {w}, {b}"
    )


def test_other_line():
    from main import train

    x = np.linspace(-1, 1, 30)
    w, b = train(x, -0.5 * x + 4, lr=0.1, steps=2000)
    assert abs(w + 0.5) < 0.01 and abs(b - 4) < 0.01
