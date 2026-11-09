"""Projects: levels, hint rules, carried-forward code, portfolio and export."""

import io
import json
import zipfile

import pytest
from conftest import REPO
from fastapi.testclient import TestClient

from dojo.api import create_app
from dojo.portfolio import to_ipynb
from dojo.registry import load_content
from dojo.store import Store

CONTENT = load_content(REPO / "content")
PROJECT = "/api/modules/projects/lessons/expense-tracker"


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "db")
    with TestClient(create_app(CONTENT, store=store)) as client:
        client.post("/api/auth/register", json={"username": "ada", "password": "password1"})
        yield client, store, store.authenticate("ada", "password1")


def test_project_lesson_payload(setup):
    client, _, _ = setup
    lesson = client.get(PROJECT).json()
    assert lesson["project"]["level"] == "guided"
    assert lesson["project"]["uses"] == ["python-basics"]
    assert lesson["view"] == "editor"  # the project overrides the module's notebook view
    checkpoint = next(s for s in lesson["steps"] if s["type"] == "exercise")["exercise"]
    assert set(checkpoint["starters"]) == {"guided", "assisted", "solo"}
    assert "TODO" in checkpoint["starters"]["guided"]
    assert "NotImplementedError" in checkpoint["starters"]["assisted"]
    assert checkpoint["submission"] is None


def test_levels_and_hint_rules(setup):
    client, _, _ = setup
    hint = f"{PROJECT}/steps/1/hints"
    assert client.get(f"{hint}/4").json()["solution"]  # guided: show me allowed
    client.put(f"{PROJECT}/level", json={"level": "assisted"})
    assert client.get(f"{hint}/1").status_code == 200
    assert client.get(f"{hint}/4").status_code == 403  # assisted: no show me
    client.put(f"{PROJECT}/level", json={"level": "solo"})
    assert client.get(PROJECT).json()["project"]["level"] == "solo"
    response = client.get(f"{hint}/1")
    assert response.status_code == 403 and "Solo" in response.json()["detail"]
    assert client.put(f"{PROJECT}/level", json={"level": "expert"}).status_code == 422


def test_levels_only_for_projects(setup):
    client, _, _ = setup
    url = "/api/modules/python-basics/lessons/01-first-program/level"
    assert client.put(url, json={"level": "solo"}).status_code == 400


def test_portfolio_and_export(setup):
    client, store, user = setup
    assert client.get("/api/portfolio").json() == []
    lesson = CONTENT.modules["projects"].lessons[0]
    exercises = list(lesson.exercises.values())
    for exercise in exercises[:-1]:
        store.save_submission(user, exercise.spec.id, "partial")
    assert client.get("/api/portfolio").json() == [], "unfinished projects aren't listed"
    store.save_submission(user, exercises[-1].spec.id, "print('final')\n")
    items = client.get("/api/portfolio").json()
    assert [i["slug"] for i in items] == ["expense-tracker"]
    assert items[0]["code"] == "print('final')\n" and len(items[0]["checkpoints"]) == 4

    response = client.get("/api/portfolio/projects/expense-tracker/export")
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert sorted(archive.namelist()) == ["README.md", "main.py"]
    readme = archive.read("README.md").decode()
    assert readme.startswith("# Expense Tracker") and "Built by **ada**" in readme
    assert client.get("/api/portfolio/projects/weather-dashboard/export").status_code == 404


def test_carry_forward_submission_in_payload(setup):
    client, store, user = setup
    first = list(CONTENT.modules["projects"].lessons[0].exercises.values())[0]
    store.save_submission(user, first.spec.id, "my own code")
    steps = client.get(PROJECT).json()["steps"]
    exercise = next(s for s in steps if s["type"] == "exercise")["exercise"]
    assert exercise["submission"] == "my own code"


def test_to_ipynb():
    notebook = json.loads(to_ipynb("# %%\nx = 1\n\n# %%\nx + 1\n"))
    assert notebook["nbformat"] == 4
    assert ["".join(c["source"]) for c in notebook["cells"]] == ["x = 1", "x + 1"]
