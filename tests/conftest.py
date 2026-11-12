from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent


@pytest.fixture
def make_content(tmp_path):
    """Write a {relative_path: text} dict under a temp content root and return the root."""

    def _make(files: dict[str, str]) -> Path:
        for rel, text in files.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return tmp_path

    return _make


def module_yaml(module_id: str, lessons=("01-intro",), prerequisites=()) -> str:
    return (
        f"id: {module_id}\ntitle: {module_id}\nlevel: beginner\n"
        f"prerequisites: [{', '.join(prerequisites)}]\n"
        f"sandbox: {{image: hoss-python}}\nlessons: [{', '.join(lessons)}]\n"
    )


def exercise_files(prefix: str, ex_id: str, starter: str, solution: str, test: str) -> dict:
    return {
        f"{prefix}/exercise.yaml": (
            f"id: {ex_id}\ntitle: t\nprompt: p\ndifficulty: 1\nhints: [h]\n"
        ),
        f"{prefix}/starter.py": starter,
        f"{prefix}/solution.py": solution,
        f"{prefix}/tests/test_visible.py": "def test_runs(run_program):\n    run_program()\n",
        f"{prefix}/tests/test_hidden.py": test,
    }
