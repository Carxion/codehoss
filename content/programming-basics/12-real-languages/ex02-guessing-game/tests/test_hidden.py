def test_range_and_first_try(run_program, monkeypatch):
    asked = []

    def fake_randint(low, high):
        asked.append((low, high))
        return 8

    monkeypatch.setattr("random.randint", fake_randint)
    lines = run_program(["8"]).lines
    assert asked == [(1, 100)], "Pick the secret once, with RANDOM(1, 100)"
    assert lines == ["Guess: 8", "Correct! Number of guesses: 1"]


def test_many_guesses(run_program, monkeypatch):
    monkeypatch.setattr("random.randint", lambda low, high: 100)
    lines = run_program(["1", "99", "100"]).lines
    assert lines[-1] == "Correct! Number of guesses: 3"
    assert lines.count("Too low") == 2
