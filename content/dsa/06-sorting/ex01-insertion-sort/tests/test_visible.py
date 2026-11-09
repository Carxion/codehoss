def test_small():
    from main import insertion_sort

    assert insertion_sort([7, 2, 5, 1, 9, 3]) == [1, 2, 3, 5, 7, 9]
