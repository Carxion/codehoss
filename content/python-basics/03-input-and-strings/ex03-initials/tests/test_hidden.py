import pytest


@pytest.mark.parametrize(
    ("typed", "initials", "username"),
    [
        ("  GRACE   hopper ", "Initials: G.H.", "Username: grace.hopper"),
        ("Alan Turing", "Initials: A.T.", "Username: alan.turing"),
    ],
)
def test_messy_names(run_program, typed, initials, username):
    got = run_program([typed]).lines[1:]
    assert got == [initials, username], f"For {typed!r} expected {[initials, username]}, got {got}"
