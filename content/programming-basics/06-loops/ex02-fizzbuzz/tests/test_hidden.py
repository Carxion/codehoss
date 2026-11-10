def expected(n):
    return [
        "FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i)
        for i in range(1, n + 1)
    ]


def test_up_to_31(run_program):
    lines = run_program(["31"]).lines[1:]
    assert lines == expected(31), "Check 15 and 30: they should be FizzBuzz"
