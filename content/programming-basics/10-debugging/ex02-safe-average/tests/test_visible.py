import pytest


@pytest.fixture
def average(run_program):
    function = run_program().vars.get("average")
    assert callable(function), "Write a FUNCTION called average (check the spelling)."
    return function


def test_two(average):
    assert average([4, 8]) == 6, f"average([4, 8]) gave {average([4, 8])}"
