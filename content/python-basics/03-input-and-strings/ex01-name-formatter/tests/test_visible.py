def test_greets_ada(run_program):
    got = run_program(["ada", "lovelace"]).last_line
    assert got == "Nice to meet you, Ada Lovelace!", f"Got {got!r}"
