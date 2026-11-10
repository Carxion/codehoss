import pytest
from dojo_checks import run_pseudo


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (200, "200 minutes is 3 hours and 20 minutes"),
        (59, "59 minutes is 0 hours and 59 minutes"),
        (120, "120 minutes is 2 hours and 0 minutes"),
    ],
)
def test_other_numbers(minutes, expected):
    out, _ = run_pseudo(replace={"minutes = 135": f"minutes = {minutes}"})
    got = out.strip().splitlines()[-1]
    assert got == expected, f"With minutes = {minutes} it showed {got!r}"
