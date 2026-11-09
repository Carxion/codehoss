import pytest


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", True),
        ("(", False),
        (")", False),
        ("print(x[0])", True),
        ("{[}", False),
        ("(()", False),
        ("a(b)c[d]{e}", True),
    ],
)
def test_cases(text, expected):
    from main import is_balanced

    assert is_balanced(text) is expected, f"is_balanced({text!r})"
