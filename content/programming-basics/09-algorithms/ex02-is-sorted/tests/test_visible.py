import pytest


@pytest.fixture
def is_sorted(run_program):
    function = run_program().vars.get("is_sorted")
    assert callable(function), "Write a FUNCTION called is_sorted (check the spelling)."
    return function


def test_examples(is_sorted):
    assert is_sorted([1, 3, 3, 7]) is True
    assert is_sorted([1, 5, 2]) is False
