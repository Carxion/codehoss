from hoss_checks import assert_fast


def test_edge_cases():
    from main import contains_duplicate

    assert contains_duplicate([]) is False
    assert contains_duplicate([7, 7]) is True


def test_fast_on_100k():
    from main import contains_duplicate

    nums = list(range(100_000))
    result = assert_fast(
        contains_duplicate,
        nums,
        budget=1.0,
        size="100,000 numbers",
        hint="Comparing every pair is O(n²); use a set to make it O(n).",
    )
    assert result is False
    assert (
        assert_fast(contains_duplicate, nums + [99_999], budget=1.0, size="100,001 numbers") is True
    )
