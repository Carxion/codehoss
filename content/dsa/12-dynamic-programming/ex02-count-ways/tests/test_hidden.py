from hoss_checks import assert_fast


def test_order_does_not_matter():
    from main import count_ways

    assert count_ways([1, 2], 3) == 2, "1+1+1 and 1+2 (2+1 is the same way)"
    assert count_ways([2], 3) == 0
    assert count_ways([3, 7], 0) == 1


def test_big():
    from main import count_ways

    coins = [1, 2, 5, 10, 20, 50, 100, 200]
    assert assert_fast(count_ways, coins, 200, budget=1.0, size="amount 200") == 73682
    assert assert_fast(count_ways, coins, 1000, budget=1.0, size="amount 1,000") == 321335886
