def story(result):
    # Ignore the echoed "> command" lines; keep what the game printed.
    return [line for line in result.lines if not line.startswith(">")]


def test_blocked_exit(run_program):
    got = story(run_program(["go west", "quit"]))
    assert got == ["You are in a dusty hall.", "You can't go that way.", "Goodbye!"], got


def test_unknown_command(run_program):
    got = story(run_program(["dance", "quit"]))
    assert got == ["You are in a dusty hall.", "I don't understand.", "Goodbye!"], got


def test_any_case(run_program):
    got = story(run_program(["GO NORTH", "  Quit "]))
    assert got == ["You are in a dusty hall.", "Books line the walls.", "Goodbye!"], got
