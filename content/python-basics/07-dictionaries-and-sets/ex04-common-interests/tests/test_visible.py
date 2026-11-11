def test_example(run_program):
    got = run_program(["Chess, hiking ,Python", "python, cooking, chess"]).lines[2:]
    assert got == ["Both: chess, python", "Only you: hiking", "Only them: cooking"], f"Got {got}"
