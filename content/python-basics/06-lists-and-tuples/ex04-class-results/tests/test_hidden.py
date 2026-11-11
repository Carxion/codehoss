def test_boundary_and_order(run_program):
    got = run_program(["Zed Amy Bo Kai", "50 49 100 0"]).lines[2:]
    expected = ["Zed: 50 pass", "Amy: 49 fail", "Bo: 100 pass", "Kai: 0 fail", "Passed: Zed, Bo"]
    assert got == expected, f"Expected {expected}, got {got}"
