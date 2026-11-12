from hoss_checks import assert_fast


def test_edges():
    from main import group_anagrams

    assert group_anagrams([]) == []
    assert group_anagrams(["a", "a"]) == [["a", "a"]]


def test_fast():
    from main import group_anagrams

    words = [f"w{i % 500}x" for i in range(50_000)]
    got = assert_fast(group_anagrams, words, budget=2.0, size="50,000 words")
    assert len(got) == len({"".join(sorted(w)) for w in words})
