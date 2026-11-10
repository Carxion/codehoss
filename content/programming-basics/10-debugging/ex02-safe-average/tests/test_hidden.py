import pytest


@pytest.fixture
def average(run_program):
    function = run_program().vars.get("average")
    assert callable(function), "Write a FUNCTION called average (check the spelling)."
    return function


def test_rounding_and_one(average):
    assert average([1, 2, 2]) == 1.67
    assert average([5]) == 5, "A single number is its own average"


def test_empty(average):
    assert average([]) == 0, "An empty list should give 0, not an error"
