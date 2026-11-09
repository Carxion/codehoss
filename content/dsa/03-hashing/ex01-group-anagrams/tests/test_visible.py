def test_example():
    from main import group_anagrams

    got = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    assert got == [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]], got
