def output(result):
    return [line for line in result.lines if not line.startswith(">")]


def test_bad_amount_and_unknown_command(run_program):
    got = output(run_program(["add food lots", "dance", "quit"]))
    assert got == ["Amount must be a number", "Unknown command", "Bye!"], got


def test_empty_report(run_program):
    got = output(run_program(["report", "quit"]))
    assert got == ["Total: 0.00", "Bye!"], got


def test_alphabetical(run_program):
    got = output(run_program(["add zoo 1", "add art 2.25", "report", "quit"]))
    assert got == ["art: 2.25", "zoo: 1.00", "Total: 3.25", "Bye!"], got
