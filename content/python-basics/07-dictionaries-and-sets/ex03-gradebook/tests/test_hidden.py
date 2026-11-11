def test_order_and_rounding(run_program):
    entries = ["zoe 70", "amy 100", "zoe 71", "zoe 72", "amy 95", ""]
    got = run_program(entries).lines[len(entries):]
    assert got == ["zoe: 3 scores, average 71.0", "amy: 2 scores, average 97.5"], f"Got {got}"


def test_book_holds_lists(run_program):
    book = run_program(["kai 10", "kai 20", ""]).vars.get("book")
    assert book == {"kai": [10, 20]}, f"book should be {{'kai': [10, 20]}}, got {book!r}"


def test_nothing_entered(run_program):
    got = run_program([""]).lines[1:]
    assert got == [], f"With no entries nothing should be printed, got {got}"
