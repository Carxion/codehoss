def test_second_try(run_program):
    got = run_program(["1111", "4321"]).lines
    assert got[1] == "Wrong PIN. Attempts left: 2" and got[-1] == "Access granted", f"Got {got}"
