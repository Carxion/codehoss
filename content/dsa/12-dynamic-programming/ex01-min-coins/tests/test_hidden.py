from hoss_checks import assert_fast


def test_edges():
    from main import min_coins

    assert min_coins([2], 3) == -1
    assert min_coins([5], 0) == 0
    assert min_coins([7, 3], 13) == 3
    assert min_coins([9, 6, 5, 1], 11) == 2


def test_big_amount():
    from main import min_coins

    result = assert_fast(
        min_coins,
        [1, 7, 23, 97, 211],
        10_000,
        budget=2.0,
        size="amount 10,000",
        hint="Fill a table from 0 up to the amount; don't recurse without remembering.",
    )
    assert result == 52
