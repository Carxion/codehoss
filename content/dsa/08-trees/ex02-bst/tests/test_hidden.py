import re
from pathlib import Path


def check_source():
    source = Path(__file__).with_name("main.py").read_text()
    assert not re.search("(?<!\\w)sorted\\(|\\.sort\\(", source), (
        "An in-order walk is already sorted: no sorted() or .sort()"
    )


def test_no_sorting():
    check_source()


def test_shape_and_duplicates():
    from main import BST

    tree = BST()
    assert tree.in_order() == [] and not tree.contains(1)
    for v in [5, 3, 8, 3, 5, 9]:
        tree.insert(v)
    assert tree.in_order() == [3, 5, 8, 9]
    assert tree.root.right.right.value == 9


def test_fast_with_50k():
    import random

    from dojo_checks import assert_fast
    from main import BST

    values = list(range(50_000))
    random.Random(7).shuffle(values)

    def build_and_search():
        tree = BST()
        for v in values:
            tree.insert(v)
        return tree, all(tree.contains(v) for v in values), tree.contains(-1)

    tree, found, missing = assert_fast(
        build_and_search,
        budget=3.0,
        size="50,000 inserts and lookups",
        hint="Walk down one branch per step instead of visiting every node.",
    )
    assert found and not missing
    assert tree.in_order()[:5] == [0, 1, 2, 3, 4]
