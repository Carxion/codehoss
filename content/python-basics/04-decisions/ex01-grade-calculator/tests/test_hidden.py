import pytest


@pytest.mark.parametrize(
    ("score", "grade"),
    [
        ("100", "A"),
        ("90", "A"),
        ("89", "B"),
        ("80", "B"),
        ("79", "C"),
        ("70", "C"),
        ("69", "D"),
        ("60", "D"),
        ("59", "F"),
        ("0", "F"),
    ],
)
def test_grade_boundaries(run_program, score, grade):
    got = run_program([score]).last_line
    assert got == f"Grade: {grade}", f"Score {score} should print 'Grade: {grade}', got {got!r}"
