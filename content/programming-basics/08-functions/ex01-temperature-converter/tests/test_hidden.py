import pytest


def test_both_ways(run_program):
    v = run_program().vars
    to_f, to_c = v.get("to_fahrenheit"), v.get("to_celsius")
    assert callable(to_f) and callable(to_c), "Write both functions: to_fahrenheit and to_celsius"
    assert to_f(0) == 32 and to_f(-40) == -40
    assert to_c(212) == 100, f"to_celsius(212) gave {to_c(212)}"
    assert to_c(32) == 0
    assert to_c(98.6) == pytest.approx(37), (
        "to_celsius(98.6) should be about 37: check the brackets"
    )
