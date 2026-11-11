import pytest


@pytest.mark.parametrize(
    ("year", "leap"),
    [(2024, True), (2023, False), (1900, False), (2000, True), (2100, False), (1600, True)],
)
def test_years(run_program, year, leap):
    expected = f"{year} is a leap year" if leap else f"{year} is not a leap year"
    got = run_program([str(year)]).last_line
    assert got == expected, f"For {year} expected {expected!r}, got {got!r}"
