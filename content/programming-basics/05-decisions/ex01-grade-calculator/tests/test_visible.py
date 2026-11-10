import pytest


@pytest.mark.parametrize(("score", "grade"), [("95", "A"), ("72", "C")])
def test_grade(run_program, score, grade):
    got = run_program([score]).last_line
    assert got == f"Grade: {grade}", f"Score {score} should show 'Grade: {grade}', got {got!r}"
