def feedback(lines):
    return [
        line for line in lines if line in ("Too low!", "Too high!") or line.startswith("Correct!")
    ]


def test_right_first_time(run_program):
    got = feedback(run_program(["7"]).lines)
    assert got == ["Correct! Guesses: 1"], (
        f"Guessing 7 straight away should end the game, got {got}"
    )


def test_five_guesses(run_program):
    got = feedback(run_program(["1", "2", "10", "8", "7"]).lines)
    expected = ["Too low!", "Too low!", "Too high!", "Too high!", "Correct! Guesses: 5"]
    assert got == expected, f"Expected {expected}, got {got}"
