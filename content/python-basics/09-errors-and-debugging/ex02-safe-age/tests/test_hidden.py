import pytest


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (" 7 ", 7),
        ("0", 0),
        ("130", 130),
        ("abc", None),
        ("3.5", None),
        ("-1", None),
        ("200", None),
        ("", None),
    ],
)
def test_parse_age(text, expected):
    from main import parse_age

    assert parse_age(text) == expected, f"parse_age({text!r}) gave {parse_age(text)!r}"
