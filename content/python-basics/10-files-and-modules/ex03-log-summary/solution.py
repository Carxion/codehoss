from pathlib import Path


def count_levels(path):
    counts = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        date, time, level, message = line.split(maxsplit=3)
        counts[level] = counts.get(level, 0) + 1
    return counts


def error_messages(path):
    messages = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        date, time, level, message = line.split(maxsplit=3)
        if level == "ERROR":
            messages.append(message)
    return messages


if __name__ == "__main__":
    Path("server.log").write_text(
        "2026-11-11 09:00:01 INFO Server started\n"
        "2026-11-11 09:07:40 ERROR Disk full\n",
        encoding="utf-8",
    )
    print(count_levels("server.log"))
    print(error_messages("server.log"))
