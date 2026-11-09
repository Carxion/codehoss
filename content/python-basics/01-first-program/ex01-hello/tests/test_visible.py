def test_first_line_says_hello(run_program):
    lines = run_program().lines
    got = lines[0] if lines else "(nothing printed)"
    assert got == "Hello, world!", f"First line should be 'Hello, world!' but was {got!r}"
