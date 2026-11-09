def feedback(lines):
    return [
        line for line in lines if line in ("Too low!", "Too high!") or line.startswith("Correct!")
    ]


def test_three_guesses(run_program):
    got = feedback(run_program(["3", "9", "7"]).lines)
    expected = ["Too low!", "Too high!", "Correct! Guesses: 3"]
    assert got == expected, f"Guesses 3, 9, 7 should give {expected}, got {got}"
