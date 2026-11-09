def test_small():
    from main import first_at_least

    nums = [1, 3, 3, 3, 7, 9]
    assert first_at_least(nums, 3) == 1
    assert first_at_least(nums, 4) == 4
    assert first_at_least(nums, 10) == 6
