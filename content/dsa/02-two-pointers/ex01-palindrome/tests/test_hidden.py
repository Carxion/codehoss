import pytest


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("race a car", False),
        ("", True),
        ("  ", True),
        ("No 'x' in Nixon", True),
        ("ab", False),
        ("0P", False),
    ],
)
def test_cases(text, expected):
    from main import is_palindrome

    assert is_palindrome(text) is expected, f"is_palindrome({text!r})"
