def test_size_3(run_program):
    got = run_program(["3"]).lines[1:]
    expected = ["   1   2   3", "   2   4   6", "   3   6   9"]
    assert got == expected, f"Expected {expected}, got {got}"
