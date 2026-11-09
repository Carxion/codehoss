import pytest
from conftest import REPO
from fastapi.testclient import TestClient

from dojo.api import create_app
from dojo.registry import load_content
from dojo.sandbox import docker_available, image_exists
from dojo.store import Store

CONTENT = load_content(REPO / "content")
LESSON = "/api/modules/python-basics/lessons/01-first-program"
needs_docker = [
    pytest.mark.docker,
    pytest.mark.skipif(
        not (docker_available() and image_exists("dojo-python")),
        reason="needs Docker and the dojo-python image (run `dojo build-images`)",
    ),
]


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    store = Store(tmp_path_factory.mktemp("db") / "dojo.db")
    return create_app(CONTENT, store=store)


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/auth/register", json={"username": "ada", "password": "password1"}
            ).status_code
            == 201
        )
        yield client


@pytest.fixture
def session_id(client):
    response = client.post("/api/sessions", json={"module_id": "python-basics"})
    assert response.status_code == 201, response.text
    yield response.json()["session_id"]


def test_requires_login(app):
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/modules").status_code == 401
        assert anonymous.get("/api/health").status_code == 200


def test_login_and_logout(app, client):
    with TestClient(app) as other:
        assert (
            other.post(
                "/api/auth/login", json={"username": "ada", "password": "wrong-pass"}
            ).status_code
            == 401
        )
        assert (
            other.post(
                "/api/auth/login", json={"username": "ada", "password": "password1"}
            ).status_code
            == 200
        )
        assert other.get("/api/me").json() == {"username": "ada"}
        other.post("/api/auth/logout")
        assert other.get("/api/me").status_code == 401


def test_modules_include_progress_counts(client):
    lesson = client.get("/api/modules").json()[0]["lessons"][0]
    assert lesson["slug"] == "01-first-program"
    assert lesson["steps"] == 9 and lesson["done"] >= 0


def test_lesson_never_leaks_answers(client):
    steps = client.get(LESSON).json()["steps"]
    try_it = next(s for s in steps if s["type"] == "try-it")
    quiz = next(s for s in steps if s["type"] == "quiz")
    exercise = next(s for s in steps if s["type"] == "exercise")["exercise"]
    assert {"solution", "check", "hints"}.isdisjoint(try_it) and try_it["hint_count"] == 2
    assert {"answer", "explanation"}.isdisjoint(quiz)
    assert {"solution", "hidden_tests", "hints"}.isdisjoint(exercise)


def test_hints_escalate_to_show_me_and_are_recorded(client):
    # Step 2 of lesson 1 is a try-it with 2 hints; level 3 is "show me".
    assert client.get(f"{LESSON}/steps/2/hints/1").json()["hint"].startswith("Only the text")
    show_me = client.get(f"{LESSON}/steps/2/hints/3").json()
    assert show_me["solution"] == 'print("Hello, Dojo!")\n'
    assert client.get(f"{LESSON}/steps/2/hints/4").status_code == 404
    progress = client.get(LESSON).json()["progress"]["2"]
    assert progress["hints_used"] == 2 and progress["showed_solution"] is True


def test_quiz_only_reveals_explanation_when_right(client):
    quiz_index = 8
    wrong = client.post(f"{LESSON}/steps/{quiz_index}/answer", json={"answer": 0}).json()
    right = client.post(f"{LESSON}/steps/{quiz_index}/answer", json={"answer": 1}).json()
    assert wrong == {"correct": False, "explanation": ""}
    assert right["correct"] is True and "quotes" in right["explanation"]
    assert client.get(LESSON).json()["progress"][str(quiz_index)]["done"] is True


def test_viewed_marks_explain_steps_done(client):
    assert client.post(f"{LESSON}/steps/0/viewed").status_code == 204
    assert client.post(f"{LESSON}/steps/2/viewed").status_code == 400  # try-it: must do it


def test_unknown_session_is_404(client):
    assert client.post("/api/sessions/nope/run", json={"code": "print(1)"}).status_code == 404


class TestSandboxed:
    pytestmark = needs_docker

    def test_sessions_are_reused_and_private(self, app, client, session_id):
        again = client.post("/api/sessions", json={"module_id": "python-basics"}).json()
        assert again["session_id"] == session_id
        with TestClient(app) as mallory:
            mallory.post(
                "/api/auth/register", json={"username": "mallory", "password": "password1"}
            )
            response = mallory.post(f"/api/sessions/{session_id}/run", json={"code": "print(1)"})
            assert response.status_code == 404

    def test_run_explains_errors(self, client, session_id):
        body = client.post(f"/api/sessions/{session_id}/run", json={"code": 'pirnt("hi")'}).json()
        assert body["explanation"]["title"] == "NameError"
        assert body["explanation"]["line"] == 1
        assert "`print`" in body["explanation"]["message"]

    def test_check_records_progress(self, client, session_id):
        solution = CONTENT.exercise("py.hello").solution_path.read_text()
        body = client.post(
            f"/api/sessions/{session_id}/check", json={"exercise_id": "py.hello", "code": solution}
        ).json()
        assert body["passed"] is True
        assert client.get(LESSON).json()["progress"]["6"]["done"] is True

    def test_try_it(self, client, session_id):
        url = f"/api/sessions/{session_id}/try-it"
        good = client.post(
            url, json={"lesson": "01-first-program", "step": 2, "code": 'print("Hello, Dojo!")'}
        ).json()
        bad = client.post(
            url, json={"lesson": "01-first-program", "step": 2, "code": 'print("nope")'}
        ).json()
        assert good["passed"] is True
        assert bad == {"passed": False, "message": "Print exactly: Hello, Dojo!"}

    def test_interactive_stream(self, client, session_id):
        code = 'name = input("Name? ")\nprint("Hi", name)'
        with client.websocket_connect(f"/api/sessions/{session_id}/stream") as ws:
            ws.send_json({"type": "run", "code": code})
            output = ""
            while "Name? " not in output:
                output += ws.receive_json()["data"]
            ws.send_json({"type": "stdin", "data": "Ada\n"})
            messages = []
            while (message := ws.receive_json())["type"] != "exit":
                messages.append(message["data"])
        assert output + "".join(messages) == "Name? Hi Ada\n"
        assert message["exit_code"] == 0 and message["cancelled"] is False

    def test_stop_button(self, client, session_id):
        with client.websocket_connect(f"/api/sessions/{session_id}/stream") as ws:
            ws.send_json({"type": "run", "code": "input('waiting forever')"})
            ws.receive_json()
            ws.send_json({"type": "stop"})
            while (message := ws.receive_json())["type"] != "exit":
                pass
        assert message["cancelled"] is True

    def test_lsp_bridge(self, client, session_id):
        with client.websocket_connect(f"/api/sessions/{session_id}/lsp") as ws:
            ws.send_json(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"processId": None, "rootUri": None, "capabilities": {}},
                }
            )
            while "id" not in (reply := ws.receive_json()) or reply.get("method"):
                pass
        assert reply["id"] == 1 and "capabilities" in reply["result"]
