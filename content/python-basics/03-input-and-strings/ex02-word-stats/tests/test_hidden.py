import pytest


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("python", ["Length: 6", "Upper: PYTHON", "Reversed: nohtyp"]),
        ("Dojo", ["Length: 4", "Upper: DOJO", "Reversed: ojoD"]),
    ],
)
def test_all_three_facts(run_program, word, expected):
    got = run_program([word]).lines[-3:]
    assert got == expected, f"For {word!r} expected {expected}, got {got}"
