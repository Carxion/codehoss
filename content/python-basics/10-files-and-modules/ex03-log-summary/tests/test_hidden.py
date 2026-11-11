LOG = """2026-11-12 08:00:00 ERROR Cannot connect to database
2026-11-12 08:00:05 INFO Retrying
2026-11-12 08:00:10 ERROR Cannot connect to database again

2026-11-12 08:01:00 DEBUG x=3
2026-11-12 08:02:00 ERROR Giving up: 3 attempts
"""


def test_count_levels(tmp_path):
    from main import count_levels

    path = tmp_path / "app.log"
    path.write_text(LOG)
    got = count_levels(path)
    assert got == {"ERROR": 3, "INFO": 1, "DEBUG": 1}, f"count_levels gave {got}"


def test_error_messages_keep_their_spaces(tmp_path):
    from main import error_messages

    path = tmp_path / "app.log"
    path.write_text(LOG)
    got = error_messages(path)
    expected = [
        "Cannot connect to database",
        "Cannot connect to database again",
        "Giving up: 3 attempts",
    ]
    assert got == expected, f"error_messages gave {got}"


def test_no_errors(tmp_path):
    from main import error_messages

    path = tmp_path / "quiet.log"
    path.write_text("2026-11-12 08:00:00 INFO All good\n")
    assert error_messages(path) == [], "With no ERROR lines the list is empty"
