def test_small():
    from main import k_smallest

    assert k_smallest([7, 3, 9, 1, 5], 3) == [1, 3, 5]
