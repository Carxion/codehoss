import re
from pathlib import Path


def check_source():
    source = Path(__file__).with_name("main.py").read_text()
    assert not re.search('(?<!\\w)sorted\\(|\\.sort\\(', source), 'Merge with a heap: no sorted() or .sort()'


def test_rules():
    check_source()


def test_edges():
    from main import merge_sorted

    assert merge_sorted([]) == []
    assert merge_sorted([[], [1], []]) == [1]
    assert merge_sorted([[2, 2], [2]]) == [2, 2, 2]


def test_big():
    from dojo_checks import assert_fast
    from main import merge_sorted

    lists = [list(range(i, 200_000, 1000)) for i in range(1000)]
    result = assert_fast(merge_sorted, lists, budget=2.0, size="1,000 lists of 200 items")
    assert result == list(range(200_000))
