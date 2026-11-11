def test_average_of_evens():
    from main import average_of_evens

    got = average_of_evens([1, 2, 3, 4])
    assert got == 3.0, f"average_of_evens([1, 2, 3, 4]) gave {got!r}, expected 3.0"
