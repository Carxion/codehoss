def test_first_try(run_program):
    got = run_program(["4321"]).lines
    assert got == ["PIN: 4321", "Access granted"], f"Got {got}"


def test_blocked_after_three(run_program):
    got = run_program(["1", "2", "3"]).lines
    expected = [
        "PIN: 1",
        "Wrong PIN. Attempts left: 2",
        "PIN: 2",
        "Wrong PIN. Attempts left: 1",
        "PIN: 3",
        "Wrong PIN. Attempts left: 0",
        "Card blocked",
    ]
    assert got == expected, f"Expected {expected}, got {got}"


def test_last_chance(run_program):
    got = run_program(["0", "9", "4321"]).lines
    assert got[-1] == "Access granted" and "Card blocked" not in got, f"Got {got}"
