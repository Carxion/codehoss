def test_three_lists():
    from main import merge_sorted

    assert merge_sorted([[1, 4, 7], [2, 5], [3, 6, 9]]) == [1, 2, 3, 4, 5, 6, 7, 9]
