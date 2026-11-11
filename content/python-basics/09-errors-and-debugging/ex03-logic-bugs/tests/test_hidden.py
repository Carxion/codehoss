def test_average_of_evens_more():
    from main import average_of_evens

    assert average_of_evens([10, 20, 5]) == 15.0, "average_of_evens([10, 20, 5]) should be 15.0"
    assert average_of_evens([1, 3]) == 0, "With no even numbers the answer is 0"


def test_count_up_to():
    from main import count_up_to

    assert count_up_to(3) == [1, 2, 3], f"count_up_to(3) gave {count_up_to(3)!r}"
    assert count_up_to(1) == [1], f"count_up_to(1) gave {count_up_to(1)!r}"


def test_longest_word():
    from main import longest_word

    got = longest_word(["hi", "hello", "hey"])
    assert got == "hello", f"longest_word(['hi', 'hello', 'hey']) gave {got!r}"
    got = longest_word(["abc", "xyz", "q"])
    assert got == "abc", f"On a tie the first word wins: expected 'abc', got {got!r}"
