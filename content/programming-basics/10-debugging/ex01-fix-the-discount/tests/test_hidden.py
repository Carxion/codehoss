import pytest


@pytest.fixture
def sale_price(run_program):
    function = run_program().vars.get("sale_price")
    assert callable(function), "Write a FUNCTION called sale_price (check the spelling)."
    return function


def test_cap(sale_price):
    assert sale_price(100, 70) == 50, "More than 50% off counts as 50% off"
    assert sale_price(100, 50) == 50


def test_small(sale_price):
    assert sale_price(10, 10) == 9
    assert sale_price(19.99, 0) == pytest.approx(19.99), "0% off leaves the price alone"
