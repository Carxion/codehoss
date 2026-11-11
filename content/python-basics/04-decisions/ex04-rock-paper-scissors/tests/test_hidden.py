import pytest


@pytest.mark.parametrize(
    ("p1", "p2", "expected"),
    [
        ("paper", "rock", "Player 1 wins"),
        ("scissors", "paper", "Player 1 wins"),
        ("rock", "paper", "Player 2 wins"),
        ("paper", "scissors", "Player 2 wins"),
        ("scissors", "rock", "Player 2 wins"),
        (" PAPER ", "paper", "Draw"),
        ("rock", "lizard", "Invalid move"),
        ("spock", "rock", "Invalid move"),
    ],
)
def test_every_outcome(run_program, p1, p2, expected):
    got = run_program([p1, p2]).last_line
    assert got == expected, f"For {p1!r} vs {p2!r} expected {expected!r}, got {got!r}"
