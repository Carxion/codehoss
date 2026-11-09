def test_full_report(run_program):
    lines = run_program(["The cat saw the dog"]).lines[1:]
    expected = ["the: 2", "cat: 1", "saw: 1", "dog: 1"]
    assert lines == expected, f"Expected {expected}, got {lines}"


def test_repeated_word(run_program):
    lines = run_program(["go GO go stop"]).lines[1:]
    assert lines == ["go: 3", "stop: 1"], f"Got {lines}"
