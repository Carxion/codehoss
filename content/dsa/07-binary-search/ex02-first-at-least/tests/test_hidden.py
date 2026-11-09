import re
from pathlib import Path


def check_source():
    source = Path(__file__).with_name("main.py").read_text()
    assert not re.search('(?<!\\w)bisect', source), 'Write the binary search yourself: no bisect module'


def test_no_bisect():
    check_source()


def test_edges():
    from main import first_at_least

    assert first_at_least([], 5) == 0
    assert first_at_least([5, 5, 5], 5) == 0
    assert first_at_least([5, 5, 5], 6) == 3
    assert first_at_least([1, 2], 0) == 0


def test_fast():
    from dojo_checks import assert_fast
    from main import first_at_least

    nums = [i // 3 for i in range(1_000_000)]
    queries = list(range(100_000, 300_000, 100))
    result = assert_fast(lambda: [first_at_least(nums, q) for q in queries], budget=1.0,
                         size="2,000 searches of 1,000,000 items", hint="Use binary search: O(log n) per search.")
    assert result == [q * 3 for q in queries]
