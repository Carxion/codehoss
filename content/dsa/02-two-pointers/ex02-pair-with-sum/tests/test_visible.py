def test_small():
    from main import pair_with_sum

    assert pair_with_sum([1, 3, 4, 6, 8, 11], 14) == (1, 5)  # 3 + 11
