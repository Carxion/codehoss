def test_ada(run_program):
    got = run_program(["ada lovelace"]).lines[1:]
    assert got == ["Initials: A.L.", "Username: ada.lovelace"], f"Got {got}"
