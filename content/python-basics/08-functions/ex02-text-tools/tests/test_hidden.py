import pytest


@pytest.mark.parametrize(
    ("text", "expected"), [("AEIOU", 5), ("rhythm", 0), ("", 0), ("Banana", 3)]
)
def test_count_vowels(text, expected):
    from main import count_vowels

    assert count_vowels(text) == expected, f"count_vowels({text!r}) gave {count_vowels(text)}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("racecar", True), ("Never odd or even", True), ("python", False), ("a", True)],
)
def test_is_palindrome(text, expected):
    from main import is_palindrome

    assert is_palindrome(text) is expected, f"is_palindrome({text!r}) gave {is_palindrome(text)!r}"
