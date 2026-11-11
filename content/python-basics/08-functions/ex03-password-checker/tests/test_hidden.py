import pytest


def test_has_digit():
    from main import has_digit

    assert has_digit("abc1") is True, "has_digit('abc1') should be True"
    assert has_digit("abc") is False, "has_digit('abc') should be False"


def test_has_upper():
    from main import has_upper

    assert has_upper("abC") is True, "has_upper('abC') should be True"
    assert has_upper("abc1!") is False, "has_upper('abc1!') should be False"


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("hello", "weak"),
        ("helloworld", "weak"),
        ("helloworld1", "medium"),
        ("Hi1!", "medium"),
        ("HelloWorld1", "medium"),
        ("HelloWorld1!", "strong"),
        ("hello world!!", "medium"),
        ("", "weak"),
    ],
)
def test_strength(password, expected):
    from main import strength

    assert strength(password) == expected, (
        f"strength({password!r}) gave {strength(password)!r}, expected {expected!r}"
    )
