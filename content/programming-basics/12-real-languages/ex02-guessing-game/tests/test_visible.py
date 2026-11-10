def test_three_guesses(run_program, monkeypatch):
    monkeypatch.setattr("random.randint", lambda low, high: 37)
    lines = run_program(["50", "25", "37"]).lines
    assert lines == [
        "Guess: 50",
        "Too high",
        "Guess: 25",
        "Too low",
        "Guess: 37",
        "Correct! Number of guesses: 3",
    ], f"Your program showed {lines}"
