def test_up_to_5(run_program):
    lines = run_program(["5"]).lines[1:]
    assert lines == ["1", "2", "Fizz", "4", "Buzz"], f"Your program showed {lines}"
