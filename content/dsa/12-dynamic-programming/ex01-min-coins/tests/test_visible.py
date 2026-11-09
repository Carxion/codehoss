def test_simple():
    from main import min_coins

    assert min_coins([1, 2, 5], 11) == 3


def test_greedy_trap():
    from main import min_coins

    assert min_coins([1, 3, 4], 6) == 2, "3 + 3 beats 4 + 1 + 1"
