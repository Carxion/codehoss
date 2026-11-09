from dojo_checks import assert_fast


def test_none_and_edges():
    from main import pair_with_sum

    assert pair_with_sum([1, 2, 3], 100) is None
    assert pair_with_sum([], 1) is None
    assert pair_with_sum([5, 5], 10) == (0, 1)


def test_fast():
    from main import pair_with_sum

    nums = list(range(0, 400_000, 2))  # 200,000 even numbers
    got = assert_fast(
        pair_with_sum,
        nums,
        1,
        budget=1.0,
        size="200,000 numbers",
        hint="Checking every pair is O(n²); move two pointers instead.",
    )
    assert got is None, "Even numbers can't sum to an odd target"
    i, j = assert_fast(pair_with_sum, nums, 399_996, budget=1.0, size="200,000 numbers")
    assert nums[i] + nums[j] == 399_996 and i < j
