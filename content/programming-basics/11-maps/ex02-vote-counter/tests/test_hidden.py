import pytest


@pytest.fixture
def winner(run_program):
    function = run_program().vars.get("winner")
    assert callable(function), "Write a FUNCTION called winner (check the spelling)."
    return function


def test_late_winner(winner):
    assert winner(["Ada", "Grace", "Grace", "Alan", "Grace", "Ada"]) == "Grace"


def test_tie_goes_to_earliest(winner):
    assert winner(["Alan", "Ada", "Ada", "Alan"]) == "Alan", (
        "On a tie, the name voted for first wins"
    )


def test_one_vote(winner):
    assert winner(["Grace"]) == "Grace"
