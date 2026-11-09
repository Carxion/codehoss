import pytest


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [
        ("  grace ", "HOPPER", "Nice to meet you, Grace Hopper!"),
        ("alan", "turing", "Nice to meet you, Alan Turing!"),
    ],
)
def test_tidies_messy_names(run_program, first, last, expected):
    got = run_program([first, last]).last_line
    assert got == expected, f"For inputs {first!r} and {last!r} expected {expected!r}, got {got!r}"
