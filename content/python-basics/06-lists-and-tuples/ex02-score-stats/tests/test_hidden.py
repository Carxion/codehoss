import pytest


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        (["10"], ["Highest: 10", "Lowest: 10", "Average: 10.0"]),
        (["5", "5", "8", "2"], ["Highest: 8", "Lowest: 2", "Average: 5.0"]),
    ],
)
def test_stats(run_program, scores, expected):
    lines = run_program([str(len(scores)), *scores]).lines[-3:]
    assert lines == expected, f"For scores {scores} expected {expected}, got {lines}"
