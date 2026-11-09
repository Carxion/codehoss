from dojo_checks import assert_fast


def test_ties_and_empty():
    from main import most_frequent

    assert most_frequent([]) is None
    assert most_frequent(["x", "y", "y", "x"]) == "y", "y reaches 2 first"
    assert most_frequent([3]) == 3


def test_fast():
    from main import most_frequent

    items = [i % 1000 for i in range(200_000)] + [7]
    assert (
        assert_fast(
            most_frequent,
            items,
            budget=1.0,
            size="200,000 items",
            hint="Count with a dictionary in one pass instead of list.count().",
        )
        == 7
    )
