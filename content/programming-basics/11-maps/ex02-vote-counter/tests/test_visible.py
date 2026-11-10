import pytest


@pytest.fixture
def winner(run_program):
    function = run_program().vars.get("winner")
    assert callable(function), "Write a FUNCTION called winner (check the spelling)."
    return function


def test_example(winner):
    assert winner(["Ada", "Alan", "Ada", "Grace"]) == "Ada"
