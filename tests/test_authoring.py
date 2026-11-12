"""Authoring: safe file access, live preview, scaffolding, reload and the Studio API."""

import shutil

import pytest
from conftest import REPO
from fastapi.testclient import TestClient

from hoss import authoring
from hoss.api import create_app
from hoss.grader import LOCAL
from hoss.registry import load_content
from hoss.store import Store
from hoss.validate import validate

LESSON = "python-basics/04-decisions/lesson.yaml"


@pytest.fixture
def root(tmp_path):
    for module in ("python-basics", "programming-basics"):
        shutil.copytree(REPO / "content" / module, tmp_path / module)
    return tmp_path


# --- access -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", ["../secret.yaml", "/etc/passwd.yaml", "a/../../x.md", "python-basics/data.csv", ""]
)
def test_only_text_files_inside_content(root, path):
    with pytest.raises(authoring.AuthoringError):
        authoring.resolve(root, path)


def test_authors():
    assert authoring.is_author("ada", "ada, bob")
    assert authoring.is_author("Bob", "ada,bob")
    assert not authoring.is_author("eve", "ada")
    assert authoring.is_author("eve", "*")
    assert not authoring.is_author("eve", "")


def test_tree_and_read_write(root):
    modules = {m["id"]: m["files"] for m in authoring.tree(root)}
    assert LESSON in modules["python-basics"]
    assert not any("__pycache__" in f for f in modules["python-basics"])
    text = authoring.read(root, LESSON)
    authoring.write(root, LESSON, text.replace("\r\n", "\n") + "# note\n")
    assert authoring.read(root, LESSON).endswith("# note\n")
    with pytest.raises(authoring.AuthoringError, match="inside a module"):
        authoring.write(root, "loose.md", "x")


# --- preview ----------------------------------------------------------------------


def test_preview_renders_the_lesson_without_saving(root):
    text = authoring.read(root, LESSON).replace("Making decisions", "Choosing paths", 1)
    result = authoring.preview(root, LESSON, text)
    assert result["markers"] == []
    assert result["lesson"]["title"] == "Choosing paths"
    exercise = next(s for s in result["lesson"]["steps"] if s["type"] == "exercise")
    assert exercise["exercise"]["prompt"] and "solution" not in str(exercise)
    assert "Making decisions" in authoring.read(root, LESSON)  # nothing written


def test_preview_points_at_the_broken_line(root):
    text = authoring.read(root, LESSON)
    lines = text.splitlines()
    quiz_line = next(i for i, ln in enumerate(lines, 1) if "type: quiz" in ln)
    broken_quiz = text.replace("type: quiz", "type: quizz", 1)
    [marker] = authoring.preview(root, LESSON, broken_quiz)["markers"]
    assert marker["line"] == quiz_line and "quizz" in marker["message"]

    broken = authoring.preview(root, LESSON, "title: [oops\n")["markers"]
    assert broken[0]["line"] == 1 and "hoss-preview" not in broken[0]["message"]

    missing = authoring.preview(root, LESSON, text.replace("ref: ex01", "ref: ex09", 1))
    gone = next(m for m in missing["markers"] if "missing folder" in m["message"])
    assert lines[gone["line"] - 1].strip().startswith("ref: ex09"[:5])


def test_locate_follows_yaml_paths():
    text = "title: x\nsteps:\n  - type: explain\n    md: hi\n  - type: quiz\n    question: q\n"
    assert authoring.locate(text, ["steps", "1", "question"]) == 6
    assert authoring.locate(text, ["steps", "0", "explain", "md"]) == 4
    assert authoring.locate(text, ["steps", "1", "options"]) == 5  # missing: its parent


# --- scaffolding ------------------------------------------------------------------


@pytest.mark.parametrize("language", ["python", "pseudo"])
def test_scaffolded_content_is_valid_and_solvable(root, language):
    authoring.new_module(root, "my-course", "My course", language)
    authoring.new_lesson(root, "my-course", "02-loops", "Loops")
    files = authoring.new_exercise(root, "my-course", "02-loops", "ex01-greet", "Greet")
    content = load_content(root)
    module = content.modules["my-course"]
    assert [les.slug for les in module.lessons] == ["01-first-lesson", "02-loops"]
    assert module.spec.language == language
    assert "ex01-greet" in module.lessons[1].exercises
    problems = [p for p in validate(content, run=False) if "my-course" in p.where]
    assert problems == []
    lesson_yaml = files[0]
    result = authoring.test_lesson(root, lesson_yaml, authoring.read(root, lesson_yaml), LOCAL)
    assert result == {"checks": 1, "markers": []}


def test_scaffolding_refuses_bad_names_and_duplicates(root):
    with pytest.raises(authoring.AuthoringError, match="valid name"):
        authoring.new_lesson(root, "python-basics", "Bad Name", "x")
    with pytest.raises(authoring.AuthoringError, match="already"):
        authoring.new_lesson(root, "python-basics", "04-decisions", "x")


def test_test_lesson_reports_a_starter_that_already_passes(root):
    authoring.new_module(root, "my-course", "My course")
    [lesson_yaml, *_] = authoring.new_exercise(root, "my-course", "01-first-lesson", "ex01-a", "A")
    starter = "my-course/01-first-lesson/ex01-a/starter.py"
    solution = authoring.read(root, "my-course/01-first-lesson/ex01-a/solution.py")
    result = authoring.test_lesson(root, starter, solution, LOCAL)
    assert any("already passes" in m["message"] for m in result["markers"])


def test_reload_keeps_the_last_good_module(root):
    content = load_content(root)
    before = content.modules["python-basics"]
    authoring.write(root, "python-basics/module.yaml", "id: [broken\n")
    problems = authoring.reload(content)
    assert problems and content.modules["python-basics"] is before
    assert list(content.modules)[0] == "programming-basics" or "python-basics" in content.modules


# --- API --------------------------------------------------------------------------


@pytest.fixture
def client(root, tmp_path):
    app = create_app(load_content(root), store=Store(tmp_path / "db.sqlite"), authors="ada")
    with TestClient(app) as client:
        yield client


def login(client, name):
    client.post("/api/auth/register", json={"username": name, "password": "password1"})


def test_studio_is_for_authors_only(client):
    login(client, "eve")
    assert client.get("/api/me").json()["author"] is False
    assert client.get("/api/author/tree").status_code == 403
    assert client.put("/api/author/file", json={"path": LESSON, "text": "x"}).status_code == 403


def test_author_edit_cycle(client, root):
    login(client, "ada")
    assert client.get("/api/me").json()["author"] is True
    tree = client.get("/api/author/tree").json()
    assert {m["id"] for m in tree["modules"]} == {"python-basics", "programming-basics"}
    text = client.get("/api/author/file", params={"path": LESSON}).json()["text"]
    preview = client.post("/api/author/preview", json={"path": LESSON, "text": text}).json()
    assert preview["lesson"]["title"] == "Making decisions"
    saved = client.put(
        "/api/author/file",
        json={"path": LESSON, "text": text.replace("Making decisions", "Choosing paths", 1)},
    ).json()
    assert saved["saved"] == LESSON
    lesson = client.get("/api/modules/python-basics/lessons/04-decisions").json()
    assert lesson["title"] == "Choosing paths"  # learners see the save straight away
    bad = client.get("/api/author/file", params={"path": "../etc/passwd"})
    assert bad.status_code == 400


def test_author_new_lesson(client):
    login(client, "ada")
    made = client.post(
        "/api/author/new",
        json={"kind": "lesson", "module": "python-basics", "slug": "13-extra", "title": "Extra"},
    )
    assert made.status_code == 201
    assert "python-basics/13-extra/lesson.yaml" in made.json()["files"]
    lesson = client.get("/api/modules/python-basics/lessons/13-extra").json()
    assert lesson["title"] == "Extra"
