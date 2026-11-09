def test_prints_the_list(run_program):
    lines = run_program().lines
    expected = ["3 items:", "- apples", "- milk", "- bread"]
    assert lines == expected, f"Expected {expected}, got {lines}"
