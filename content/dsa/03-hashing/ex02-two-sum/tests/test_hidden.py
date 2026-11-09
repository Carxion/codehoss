from dojo_checks import assert_fast


def test_cases():
    from main import two_sum

    assert two_sum([3, 2, 4], 6) == (1, 2)
    assert two_sum([3, 3], 6) == (0, 1)
    assert two_sum([1, 2], 7) is None


def test_fast():
    from main import two_sum

    nums = list(range(200_000, 0, -1))
    i, j = assert_fast(
        two_sum,
        nums,
        3,
        budget=1.0,
        size="200,000 numbers",
        hint="Checking every pair is O(n²); remember complements in a dictionary.",
    )
    assert nums[i] + nums[j] == 3 and i < j
