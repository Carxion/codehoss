import pytest


@pytest.fixture
def find(run_program):
    function = run_program().vars.get("find")
    assert callable(function), "Write a FUNCTION called find (check the spelling)."
    return function


def test_missing(find):
    assert find(["cat", "dog", "fox"], "owl") == -1


def test_first_match_and_ends(find):
    assert find([5, 3, 5], 5) == 0, "Return the first position it appears at"
    assert find([1, 2, 3], 3) == 2, "Check the last item too"
    assert find([], 1) == -1, "An empty list contains nothing"
