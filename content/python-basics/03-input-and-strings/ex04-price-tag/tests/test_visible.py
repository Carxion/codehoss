def test_laptop(run_program):
    got = run_program(["laptop", "1249.5", "3"]).lines[3:]
    assert got == ["LAPTOP", "Price: $1249.50", "Total: $3,748.50"], f"Got {got}"
