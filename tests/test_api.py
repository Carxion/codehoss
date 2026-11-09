import pytest
from conftest import REPO
from fastapi.testclient import TestClient

from dojo.api import create_app
from dojo.registry import load_content
from dojo.sandbox import docker_available, image_exists

CONTENT = load_content(REPO / "content")
needs_docker = [
    pytest.mark.docker,
    pytest.mark.skipif(
        not (docker_available() and image_exists("dojo-python")),
        reason="needs Docker and the dojo-python image (run `dojo build-images`)",
    ),
]


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(CONTENT)) as client:
        yield client


@pytest.fixture
def session_id(client):
    response = client.post("/sessions", json={"module_id": "python-basics"})
    assert response.status_code == 201, response.text
    yield response.json()["session_id"]
    client.delete(f"/sessions/{response.json()['session_id']}")


def test_modules(client):
    modules = client.get("/modules").json()
    assert modules[0]["id"] == "python-basics"
    assert "py.hello" in modules[0]["lessons"][0]["exercises"]


def test_exercise_never_leaks_solution_or_hidden_tests(client):
    body = client.get("/exercises/py.hello").json()
    assert body["starter"].startswith("# Print two lines")
    assert "solution" not in body and "hidden_tests" not in body and "hints" not in body
    assert body["hint_count"] == 3


def test_hints_one_at_a_time(client):
    assert client.get("/exercises/py.hello/hints/1").json()["hint"].startswith("Use one print")
    assert client.get("/exercises/py.hello/hints/9").status_code == 404


def test_unknown_session_is_404(client):
    assert client.post("/sessions/nope/run", json={"code": "print(1)"}).status_code == 404


class TestSandboxed:
    pytestmark = needs_docker

    def test_run(self, client, session_id):
        body = client.post(
            f"/sessions/{session_id}/run", json={"code": "print(input() * 2)", "inputs": ["ab"]}
        ).json()
        assert body == {"stdout": "abab\n", "stderr": "", "exit_code": 0, "timed_out": False}

    def test_check(self, client, session_id):
        solution = CONTENT.exercise("py.hello").solution_path.read_text()
        body = client.post(
            f"/sessions/{session_id}/check", json={"exercise_id": "py.hello", "code": solution}
        ).json()
        assert body["passed"] is True
        assert [r["outcome"] for r in body["results"]] == ["passed", "passed"]

    def test_try_it(self, client, session_id):
        # Step 2 of lesson 1: print "Hello, Dojo!"
        url = f"/sessions/{session_id}/try-it"
        good = client.post(url, json={"lesson": "01-first-program", "step": 2,
                                      "code": 'print("Hello, Dojo!")'}).json()  # fmt: skip
        bad = client.post(url, json={"lesson": "01-first-program", "step": 2,
                                     "code": 'print("nope")'}).json()  # fmt: skip
        assert good["passed"] is True
        assert bad == {"passed": False, "message": "Print exactly: Hello, Dojo!"}

    def test_stream(self, client, session_id):
        with client.websocket_connect(f"/sessions/{session_id}/stream") as ws:
            ws.send_json({"code": "for i in range(3):\n    print(i)"})
            messages = []
            while True:
                message = ws.receive_json()
                messages.append(message)
                if message["type"] == "exit":
                    break
        output = "".join(m["data"] for m in messages if m["type"] == "output")
        assert output == "0\n1\n2\n"
        assert messages[-1] == {"type": "exit", "exit_code": 0, "timed_out": False}
