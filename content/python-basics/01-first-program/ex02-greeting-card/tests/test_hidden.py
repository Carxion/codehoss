BORDER = "+-----------------+"


def test_middle_line_is_exact(run_program):
    lines = run_program().lines
    got = lines[1] if len(lines) > 1 else "(missing)"
    assert got == "|  Happy coding!  |", f"Middle line was {got!r}"


def test_bottom_matches_top(run_program):
    lines = run_program().lines
    assert lines[:1] == [BORDER] and lines[-1:] == [BORDER], (
        "Top and bottom lines should be the border"
    )
