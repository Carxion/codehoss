import pytest


@pytest.mark.parametrize(("age", "tuesday", "price"), [("30", "no", 12), ("30", "yes", 10)])
def test_adult_price(run_program, age, tuesday, price):
    got = run_program([age, tuesday]).last_line
    assert got == f"Price: {price}", (
        f"Age {age}, Tuesday={tuesday}: expected 'Price: {price}', got {got!r}"
    )
