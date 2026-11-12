import re
from pathlib import Path


def check_source():
    source = Path(__file__).with_name("main.py").read_text()
    assert not re.search("(?<!\\w)sorted\\(|\\.sort\\(|(?<!\\w)nsmallest", source), (
        "Use heappush/heappop: no sorted(), .sort() or nsmallest"
    )


def test_rules():
    check_source()


def test_edges():
    from main import k_smallest

    nums = [4, 4, 1]
    assert k_smallest(nums, 2) == [1, 4]
    assert nums == [4, 4, 1], "don't change the caller's list"
    assert k_smallest([2, 1], 5) == [1, 2]
    assert k_smallest([], 3) == []
    assert k_smallest([3, 1], 0) == []


def test_big():
    import random

    from hoss_checks import assert_fast
    from main import k_smallest

    nums = list(range(200_000))
    random.Random(3).shuffle(nums)
    assert assert_fast(k_smallest, nums, 10, budget=1.0, size="200,000 numbers") == list(range(10))
