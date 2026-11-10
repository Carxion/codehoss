import pytest


@pytest.fixture
def is_sorted(run_program):
    function = run_program().vars.get("is_sorted")
    assert callable(function), "Write a FUNCTION called is_sorted (check the spelling)."
    return function


def test_edges(is_sorted):
    assert is_sorted([]) is True, "An empty list is sorted"
    assert is_sorted([4]) is True, "One number is sorted"
    assert is_sorted([1, 2, 3, 0]) is False, "Check the last pair too"
    assert is_sorted([9, 1, 2, 3]) is False, "Check the first pair too"
