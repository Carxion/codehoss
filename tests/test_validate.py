from conftest import REPO, exercise_files, module_yaml

from dojo.registry import load_content
from dojo.validate import _generic, validate

PASSING_TEST = "def test_x(run_program):\n    assert run_program().vars.get('x') == 1\n"
LESSON = "title: Intro\nsteps:\n  - type: exercise\n    ref: ex01\n"


def _messages(root, run=True):
    return [(p.level, p.message) for p in validate(load_content(root), run=run)]


def test_shipped_content_is_valid():
    problems = validate(load_content(REPO / "content"))
    errors = [p for p in problems if p.level == "error"]
    assert errors == [], "\n".join(f"{p.where}: {p.message}" for p in errors)


def test_good_module_has_no_problems(make_content):
    root = make_content(
        {
            "mod-a/module.yaml": module_yaml("mod-a"),
            "mod-a/01-intro/lesson.yaml": LESSON,
            **exercise_files("mod-a/01-intro/ex01", "a.one", "x = 0\n", "x = 1\n", PASSING_TEST),
        }
    )
    assert _messages(root) == []


def test_starter_that_already_passes_is_an_error(make_content):
    root = make_content(
        {
            "mod-a/module.yaml": module_yaml("mod-a"),
            "mod-a/01-intro/lesson.yaml": LESSON,
            **exercise_files("mod-a/01-intro/ex01", "a.one", "x = 1\n", "x = 1\n", PASSING_TEST),
        }
    )
    assert ("error", "starter.py already passes all tests") in _messages(root)


def test_broken_solution_is_an_error(make_content):
    root = make_content(
        {
            "mod-a/module.yaml": module_yaml("mod-a"),
            "mod-a/01-intro/lesson.yaml": LESSON,
            **exercise_files("mod-a/01-intro/ex01", "a.one", "x = 0\n", "x = 2\n", PASSING_TEST),
        }
    )
    assert any(m.startswith("reference solution fails") for _, m in _messages(root))


def test_try_it_starter_and_solution_are_checked(make_content):
    lesson = (
        "title: Intro\nsteps:\n"
        "  - type: try-it\n    prompt: p\n    starter: 'x = 1'\n    solution: 'x = 3'\n"
        "    check: 'assert x == 1'\n    hints: [h]\n"
    )
    root = make_content(
        {"mod-a/module.yaml": module_yaml("mod-a"), "mod-a/01-intro/lesson.yaml": lesson}
    )
    messages = [m for _, m in _messages(root)]
    assert "starter already passes the check" in messages
    assert any(m.startswith("solution fails its check") for m in messages)


def test_structural_problems(make_content):
    root = make_content(
        {
            "mod-a/module.yaml": module_yaml("mod-a", prerequisites=["mod-b"]),
            "mod-a/01-intro/lesson.yaml": LESSON,
            "mod-b/module.yaml": module_yaml("mod-b", prerequisites=["mod-a", "nope"]),
            "mod-b/01-intro/lesson.yaml": "title: t\nsteps:\n  - type: explain\n    md: hi\n",
            **exercise_files("mod-b/01-intro/ex09", "b.nine", "x = 0\n", "x = 1\n", PASSING_TEST),
            "wrong-name/module.yaml": module_yaml("other", lessons=["missing"]),
        }
    )
    messages = _messages(root, run=False)
    assert ("error", "exercise step refers to missing folder 'ex01'") in messages
    assert ("error", "unknown prerequisite 'nope'") in messages
    assert ("warning", "exercise 'ex09' is never used in a step") in messages
    assert ("error", "id 'other' must match folder name 'wrong-name'") in messages
    assert ("error", "lesson 'missing' has no missing/lesson.yaml") in messages
    assert any(m.startswith("prerequisite cycle") for _, m in messages)


def test_duplicate_exercise_ids(make_content):
    lesson = LESSON + "  - type: exercise\n    ref: ex02\n"
    root = make_content(
        {
            "mod-a/module.yaml": module_yaml("mod-a"),
            "mod-a/01-intro/lesson.yaml": lesson,
            **exercise_files("mod-a/01-intro/ex01", "same", "x = 0\n", "x = 1\n", PASSING_TEST),
            **exercise_files("mod-a/01-intro/ex02", "same", "x = 0\n", "x = 1\n", PASSING_TEST),
        }
    )
    assert any("is already used by" in m for _, m in _messages(root, run=False))


def _with_guide(make_content, guide_yaml):
    files = exercise_files(
        "mod-a/01-intro/ex01",
        "a.one",
        "x = 0\n",
        "total = 40 + 2\nhalf = total / 2\nprint(None)\nx = 1\n",
        PASSING_TEST,
    )
    files["mod-a/01-intro/ex01/exercise.yaml"] += f"guide:\n{guide_yaml}"
    return make_content(
        {
            "mod-a/module.yaml": module_yaml("mod-a"),
            "mod-a/01-intro/lesson.yaml": LESSON,
            **files,
        }
    )


def test_a_guide_on_another_problem_is_fine(make_content):
    root = _with_guide(make_content, "  - md: Add things up\n    code: 'price = 3 + 4'\n")
    assert _messages(root) == []


def test_a_guide_that_repeats_the_solution_is_a_warning(make_content):
    root = _with_guide(make_content, "  - code: |\n      total = 40 + 2\n      print(total)\n")
    assert ("warning", "repeats solution lines: total=40+2") in _messages(root, run=False)


def test_generic_shared_lines_are_fine(make_content):
    root = _with_guide(make_content, "  - code: |\n      print(None)\n      price = 3\n")
    assert _messages(root, run=False) == []


def test_generic_lines():
    assert _generic("except ValueError as e:")
    assert _generic("    return None  # nothing found")
    assert _generic('if x in "aeiou":')
    assert _generic("return json.load(f)")
    assert not _generic("for row in csv.DictReader(f):")
    assert not _generic("total = sum(prices)")
    assert not _generic("if total > 0:")


def test_a_guide_example_that_crashes_is_an_error(make_content):
    root = _with_guide(make_content, "  - code: 'print(1 / 0)'\n")
    assert any(level == "error" and m.startswith("example fails") for level, m in _messages(root))
