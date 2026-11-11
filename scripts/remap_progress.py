"""Move saved progress to the right steps after lessons gain, lose or reorder steps.

    uv run python scripts/remap_progress.py --since HEAD --dry-run
    uv run python scripts/remap_progress.py --since HEAD

Progress and review cards are keyed by step position ("05-loops/7"), so inserting a step
shifts every later one. This compares each lesson with its version at a git ref, matches
steps by content (exercise folder, try-it prompt, quiz question, text, code), moves rows
to their new positions, and deletes rows whose step no longer exists (left alone they
would mark an unrelated step as done). The database is copied to a .bak file first.

Run it once per change, before committing the new lessons: a second run against the same
ref would move the already-moved rows again.
"""

import argparse
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
TABLES = ("progress", "reviews")


def step_key(step: dict) -> tuple:
    kind = step.get("type")
    field = {
        "exercise": "ref",
        "try-it": "prompt",
        "quiz": "question",
        "explain": "md",
        "example": "code",
        "showcase": "algorithm",
    }.get(kind, "md")
    return kind, str(step.get(field, "")).strip()


def old_lesson(ref: str, path: Path) -> dict | None:
    rel = path.relative_to(ROOT).as_posix()
    shown = subprocess.run(
        ["git", "show", f"{ref}:{rel}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    return yaml.safe_load(shown.stdout) if shown.returncode == 0 else None


def mapping_for(old_steps: list, new_steps: list) -> dict[int, int | None]:
    """Old index -> new index, or None when the step is gone. Duplicate keys pair up in order."""
    free: dict[tuple, list[int]] = {}
    for i, step in enumerate(new_steps):
        free.setdefault(step_key(step), []).append(i)
    return {i: (free.get(step_key(s)) or [None]).pop(0) for i, s in enumerate(old_steps)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--since", default="HEAD", help="git ref with the old lessons")
    parser.add_argument("--db", type=Path, default=ROOT / "var" / "dojo.db")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    moves: list[tuple[str, str, str | None]] = []  # module, old ref, new ref (None: delete)
    for path in sorted(CONTENT.glob("*/*/lesson.yaml")):
        old = old_lesson(args.since, path)
        new = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not old or old == new:
            continue
        module, lesson = path.parent.parent.name, path.parent.name
        for i, j in mapping_for(old["steps"], new["steps"]).items():
            if i != j:
                moves.append((module, f"{lesson}/{i}", None if j is None else f"{lesson}/{j}"))

    db = sqlite3.connect(args.db)
    for module, old_ref, new_ref in moves:
        rows = sum(
            db.execute(
                f"SELECT COUNT(*) FROM {t} WHERE module_id = ? AND step_ref = ?", (module, old_ref)
            ).fetchone()[0]
            for t in TABLES
        )
        if rows:
            print(f"{module} {old_ref} -> {new_ref or 'deleted'} ({rows} row(s))")
    if args.dry_run or not moves:
        print("dry run: nothing changed" if args.dry_run else "nothing to move")
        return

    backup = args.db.with_suffix(f".db.bak-{int(time.time())}")
    shutil.copy2(args.db, backup)
    with db:
        # Two phases, so a step moving onto a position another step is leaving can't clash.
        for module, old_ref, new_ref in moves:
            for t in TABLES:
                if new_ref is None:
                    db.execute(
                        f"DELETE FROM {t} WHERE module_id = ? AND step_ref = ?", (module, old_ref)
                    )
                else:
                    db.execute(
                        f"UPDATE {t} SET step_ref = ? WHERE module_id = ? AND step_ref = ?",
                        (f"moving:{new_ref}", module, old_ref),
                    )
        for t in TABLES:
            db.execute(
                f"UPDATE {t} SET step_ref = substr(step_ref, 8) WHERE step_ref LIKE 'moving:%'"
            )
    print(f"done; backup at {backup}")


if __name__ == "__main__":
    main()
