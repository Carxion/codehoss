from pathlib import Path


def count_levels(path):
    # TODO: return a dictionary counting each level (INFO, WARNING, ERROR, ...)
    return {}


def error_messages(path):
    # TODO: return the messages of the ERROR lines, in order
    return []


if __name__ == "__main__":
    Path("server.log").write_text(
        "2026-11-11 09:00:01 INFO Server started\n"
        "2026-11-11 09:07:40 ERROR Disk full\n",
        encoding="utf-8",
    )
    print(count_levels("server.log"))
    print(error_messages("server.log"))
