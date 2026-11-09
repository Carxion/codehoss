import pytest


@pytest.mark.parametrize(
    ("age", "tuesday", "price"),
    [
        ("4", "no", 0),
        ("3", "yes", 0),
        ("5", "no", 8),
        ("17", "no", 8),
        ("10", "yes", 6),
        ("18", "no", 12),
        ("64", "no", 12),
        ("65", "no", 6),
        ("70", "yes", 4),
    ],
)
def test_price_table(run_program, age, tuesday, price):
    got = run_program([age, tuesday]).last_line
    assert got == f"Price: {price}", (
        f"Age {age}, Tuesday={tuesday}: expected 'Price: {price}', got {got!r}"
    )
