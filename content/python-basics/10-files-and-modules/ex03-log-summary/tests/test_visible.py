LOG = """2026-11-11 09:00:01 INFO Server started
2026-11-11 09:05:12 WARNING Disk 85% full

2026-11-11 09:07:40 ERROR Disk full
2026-11-11 09:08:00 INFO Cleanup finished
"""


def test_count_levels(tmp_path):
    from main import count_levels

    path = tmp_path / "server.log"
    path.write_text(LOG)
    got = count_levels(path)
    assert got == {"INFO": 2, "WARNING": 1, "ERROR": 1}, f"count_levels gave {got}"
