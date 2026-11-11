def test_mean_any_count():
    from main import mean

    assert mean(7) == 7, f"mean(7) gave {mean(7)!r}"
    assert mean(1, 2, 3, 4) == 2.5, f"mean(1, 2, 3, 4) gave {mean(1, 2, 3, 4)!r}"
    assert mean() == 0, f"mean() with nothing should give 0, got {mean()!r}"


def test_summary():
    from main import summary

    assert summary([3, 8, 4]) == (3, 8, 5.0), f"summary([3, 8, 4]) gave {summary([3, 8, 4])!r}"
    got = summary([1, 2, 2], decimals=2)
    assert got == (1, 2, 1.67), f"summary([1, 2, 2], decimals=2) gave {got!r}"


def test_add_score_to_a_given_list():
    from main import add_score

    mine = [1]
    assert add_score(5, mine) == [1, 5]
    assert mine == [1, 5], "add_score should add to the list it was given"


def test_add_score_starts_fresh_each_time():
    from main import add_score

    add_score(1)
    got = add_score(2)
    assert got == [2], (
        f"add_score(2) after add_score(1) gave {got!r}. Each call without a list needs a "
        "fresh list: default to None and create the list inside the function."
    )
