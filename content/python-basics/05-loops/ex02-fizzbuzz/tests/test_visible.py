def expected(n):
    words = []
    for i in range(1, n + 1):
        words.append(
            "FizzBuzz"
            if i % 15 == 0
            else "Fizz"
            if i % 3 == 0
            else "Buzz"
            if i % 5 == 0
            else str(i)
        )
    return words


def test_first_five(run_program):
    got = run_program(["5"]).lines[-5:]
    assert got == expected(5), f"Expected {expected(5)}, got {got}"
