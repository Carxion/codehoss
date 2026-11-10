import pytest


@pytest.fixture
def to_fahrenheit(run_program):
    function = run_program().vars.get("to_fahrenheit")
    assert callable(function), "Write a FUNCTION called to_fahrenheit (check the spelling)."
    return function


def test_boiling(to_fahrenheit):
    assert to_fahrenheit(100) == 212, f"to_fahrenheit(100) gave {to_fahrenheit(100)}"
