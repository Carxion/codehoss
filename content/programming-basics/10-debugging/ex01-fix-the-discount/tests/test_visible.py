import pytest


@pytest.fixture
def sale_price(run_program):
    function = run_program().vars.get("sale_price")
    assert callable(function), "Write a FUNCTION called sale_price (check the spelling)."
    return function


def test_quarter_off(sale_price):
    assert sale_price(80, 25) == 60, f"sale_price(80, 25) gave {sale_price(80, 25)}"
