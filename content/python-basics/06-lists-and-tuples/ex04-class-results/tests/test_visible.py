def test_example(run_program):
    got = run_program(["Ana Ben Cy", "81 45 67"]).lines[2:]
    assert got == ["Ana: 81 pass", "Ben: 45 fail", "Cy: 67 pass", "Passed: Ana, Cy"], f"Got {got}"
