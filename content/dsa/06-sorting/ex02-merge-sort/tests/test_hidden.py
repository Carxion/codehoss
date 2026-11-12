import random
from pathlib import Path

from hoss_checks import assert_fast


def no_builtin_sort():
    source = Path(__file__).with_name("main.py").read_text()
    assert "sorted(" not in source and ".sort(" not in source, (
        "Write the sort yourself: no sorted() or .sort()"
    )


def test_cases_and_speed():
    from main import merge_sort

    no_builtin_sort()
    assert (
        merge_sort([]) == [] and merge_sort([2, 1]) == [1, 2] and merge_sort([5, 5, 1]) == [1, 5, 5]
    )
    nums = random.Random(1).sample(range(1_000_000), 50_000)
    got = assert_fast(
        merge_sort,
        nums,
        budget=3.0,
        size="50,000 numbers",
        hint="An O(n²) sort is too slow here; split, sort the halves, and merge.",
    )
    assert got == sorted(nums)
