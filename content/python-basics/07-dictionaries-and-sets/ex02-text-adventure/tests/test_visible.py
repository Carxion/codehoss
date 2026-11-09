def story(result):
    # Ignore the echoed "> command" lines; keep what the game printed.
    return [line for line in result.lines if not line.startswith(">")]


def test_walk_around(run_program):
    got = story(run_program(["go north", "go south", "go east", "quit"]))
    expected = [
        "You are in a dusty hall.",
        "Books line the walls.",
        "You are in a dusty hall.",
        "It smells of old bread.",
        "Goodbye!",
    ]
    assert got == expected, f"Expected {expected}, got {got}"
