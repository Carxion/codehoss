import pytest


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


@pytest.mark.parametrize("n", [1, 15, 30])
def test_counts_to_n(run_program, n):
    got = run_program([str(n)]).lines[-n:]
    assert got == expected(n), f"For n={n} expected {expected(n)}, got {got}"
