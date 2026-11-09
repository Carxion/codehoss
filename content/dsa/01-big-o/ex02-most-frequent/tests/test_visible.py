def test_basic():
    from main import most_frequent

    assert most_frequent(["a", "b", "a", "c", "a"]) == "a"
