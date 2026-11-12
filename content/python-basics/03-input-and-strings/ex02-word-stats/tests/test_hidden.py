import pytest


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("python", ["Length: 6", "Upper: PYTHON", "Reversed: nohtyp"]),
        ("Hoss", ["Length: 4", "Upper: HOSS", "Reversed: ssoH"]),
    ],
)
def test_all_three_facts(run_program, word, expected):
    got = run_program([word]).lines[-3:]
    assert got == expected, f"For {word!r} expected {expected}, got {got}"
