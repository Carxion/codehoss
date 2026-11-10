import pytest


@pytest.mark.parametrize(
    ("score", "grade"),
    [
        ("90", "A"),
        ("89", "B"),
        ("80", "B"),
        ("79", "C"),
        ("60", "D"),
        ("59", "F"),
        ("0", "F"),
        ("100", "A"),
    ],
)
def test_boundaries(run_program, score, grade):
    got = run_program([score]).last_line
    assert got == f"Grade: {grade}", f"Score {score} should show 'Grade: {grade}', got {got!r}"
