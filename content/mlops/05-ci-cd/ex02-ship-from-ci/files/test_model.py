from model import fit, mean_absolute_error, predict


def test_fits_a_straight_line():
    rows = [{"x": x, "price": 3 * x + 10} for x in range(10)]
    weights = fit(rows, ["x"])
    assert abs(weights[0] - 10) < 1e-6 and abs(weights[1] - 3) < 1e-6
    assert abs(predict(weights, ["x"], {"x": 100}) - 310) < 1e-6
    assert mean_absolute_error(weights, ["x"], rows) < 1e-6
