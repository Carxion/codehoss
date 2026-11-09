def test_small():
    from main import merge_sort

    assert merge_sort([8, 3, 5, 1, 9, 2, 7, 4]) == [1, 2, 3, 4, 5, 7, 8, 9]
