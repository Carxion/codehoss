import pytest


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2 + 3", 5.0), ("2.5 * 4", 10.0), ("10 - 12", -2.0), ("7 / 2", 3.5)],
)
def test_calculate(text, expected):
    from main import calculate

    assert calculate(text) == expected, f"calculate({text!r}) gave {calculate(text)!r}"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("5 +", "use the form: number operator number"),
        ("1 + 2 + 3", "use the form: number operator number"),
        ("seven * 2", "not a number: seven"),
        ("3 * x", "not a number: x"),
        ("2 ^ 3", "unknown operator: ^"),
    ],
)
def test_calculate_raises(text, message):
    from main import calculate

    with pytest.raises(ValueError) as caught:
        calculate(text)
    assert str(caught.value) == message, (
        f"calculate({text!r}) raised ValueError({str(caught.value)!r}), expected {message!r}"
    )


def test_divide_by_zero_is_left_to_python():
    from main import calculate

    with pytest.raises(ZeroDivisionError):
        calculate("1 / 0")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7 / 2", "= 3.5"),
        ("2 ^ 3", "Error: unknown operator: ^"),
        ("1 / 0", "Error: can't divide by zero"),
        ("x + 1", "Error: not a number: x"),
    ],
)
def test_answer(text, expected):
    from main import answer

    assert answer(text) == expected, f"answer({text!r}) gave {answer(text)!r}, expected {expected!r}"
