import pytest


@pytest.mark.parametrize(
    ("year", "leap"),
    [
        ("1900", False),
        ("2000", True),
        ("2100", False),
        ("1996", True),
        ("2400", True),
        ("2019", False),
    ],
)
def test_century_rules(run_program, year, leap):
    expected = f"{year} is a leap year" if leap else f"{year} is not a leap year"
    got = run_program([year]).last_line
    assert got == expected, f"For {year} expected {expected!r}, got {got!r}"
