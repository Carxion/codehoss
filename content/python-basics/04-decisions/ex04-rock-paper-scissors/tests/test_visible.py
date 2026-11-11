def test_rock_beats_scissors(run_program):
    got = run_program(["Rock", "scissors"]).last_line
    assert got == "Player 1 wins", f"Got {got!r}"
