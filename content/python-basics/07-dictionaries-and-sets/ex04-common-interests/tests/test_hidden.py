def test_nothing_shared(run_program):
    got = run_program(["art,music", "Rugby"]).lines[2:]
    assert got == ["Both: (none)", "Only you: art, music", "Only them: rugby"], f"Got {got}"


def test_same_interests_with_repeats(run_program):
    got = run_program(["Go, go, Maths", "maths,GO"]).lines[2:]
    assert got == ["Both: go, maths", "Only you: (none)", "Only them: (none)"], f"Got {got}"
