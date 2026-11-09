def test_example():
    from main import flatten

    assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]
