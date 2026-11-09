def test_cases():
    from main import flatten

    assert flatten([]) == []
    assert flatten([[[]]]) == []
    assert flatten([[1], [[2]], [[[3]]]]) == [1, 2, 3]
    assert flatten(["a", ["b"]]) == ["a", "b"]
