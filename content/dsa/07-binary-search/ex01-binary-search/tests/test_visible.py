def test_small():
    from main import binary_search

    nums = [2, 5, 8, 12, 16, 23, 38]
    assert binary_search(nums, 23) == 5
    assert binary_search(nums, 2) == 0
    assert binary_search(nums, 7) == -1
