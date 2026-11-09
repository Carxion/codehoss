def output(result):
    return [line for line in result.lines if not line.startswith(">")]


def test_report(run_program):
    got = output(run_program(["add food 12.5", "add rent 500", "add food 7.5", "report", "quit"]))
    expected = ["food: 20.00", "rent: 500.00", "Total: 520.00", "Bye!"]
    assert got == expected, f"Expected {expected}, got {got}"
