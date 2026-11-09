def test_sigmoid():
    from main import sigmoid

    assert abs(sigmoid(0) - 0.5) < 1e-9
