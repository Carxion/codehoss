"""Notebook kernels in the Data Science sandbox. Needs Docker + `hoss build-images`."""

import queue
import time

import pytest
from conftest import REPO

from hoss.grader import grade
from hoss.notebook import Kernel
from hoss.registry import load_content
from hoss.sandbox import SessionManager, docker_available, image_exists

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        not (docker_available() and image_exists("hoss-ds")),
        reason="needs Docker and the hoss-ds image (run `hoss build-images`)",
    ),
]


@pytest.fixture(scope="module")
def content():
    return load_content(REPO / "content")


@pytest.fixture(scope="module")
def session(content):
    manager = SessionManager(content)
    session = manager.create("data-science")
    yield session
    manager.close(session.id)


class Client:
    def __init__(self, container):
        self.inbox: queue.Queue[dict] = queue.Queue()
        self.kernel = Kernel(container, self.inbox.put)

    def run(self, code, timeout=90):
        cell = f"c{id(code)}"
        self.kernel.execute(code, cell)
        messages = []
        while True:
            message = self.inbox.get(timeout=timeout)
            if message.get("type") == "dead":
                raise AssertionError(message["reason"])
            if message.get("cell") != cell:
                continue
            messages.append(message)
            if message["type"] == "done":
                return messages


@pytest.fixture(scope="module")
def kernel(session):
    client = Client(session.container)
    yield client
    client.kernel.close()


def kinds(messages):
    return [m["type"] for m in messages]


def test_last_expression_is_shown(kernel):
    messages = kernel.run("x = 21\nx * 2")
    result = next(m for m in messages if m["type"] == "result")
    assert result["data"]["text/plain"] == "42"
    assert messages[-1]["status"] == "ok"


def test_variables_persist_between_cells(kernel):
    kernel.run("persisted = 'still here'")
    messages = kernel.run("print(persisted)")
    assert any(m["type"] == "stream" and "still here" in m["text"] for m in messages)


def test_dataframes_render_as_html(kernel):
    messages = kernel.run("import pandas as pd\ndf = pd.read_csv('/data/grades.csv')\ndf.head(3)")
    result = next(m for m in messages if m["type"] == "result")
    assert "<table" in result["data"]["text/html"]


def test_charts_render_as_png(kernel):
    messages = kernel.run("import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])\nplt.title('t')")
    assert any(m["type"] == "display" and "image/png" in m["data"] for m in messages)


def test_errors_are_explained(kernel):
    messages = kernel.run("a = 1\nprnt(a)")
    error = next(m for m in messages if m["type"] == "error")
    assert error["ename"] == "NameError"
    assert "`print`" in error["explanation"]
    assert error["line"] == 2
    assert messages[-1]["status"] == "error"


def test_datasets_are_read_only(kernel):
    messages = kernel.run("open('/data/grades.csv', 'a')")
    error = next(m for m in messages if m["type"] == "error")
    assert error["ename"] in {"OSError", "PermissionError"}


def test_no_keyboard_input(kernel):
    messages = kernel.run("input('name?')")
    assert any(m["type"] == "error" for m in messages)


def test_interrupt(kernel):
    cell = "long"
    kernel.kernel.execute("import time\nwhile True:\n    time.sleep(0.1)", cell)
    time.sleep(2)  # the loop prints nothing, so give it a moment to start
    kernel.kernel.interrupt()
    messages = []
    while (message := kernel.inbox.get(timeout=30))["type"] != "done" or message["cell"] != cell:
        messages.append(message)
    assert message["status"] == "error"
    # The kernel survives an interrupt.
    assert kernel.run("1 + 1")[-1]["status"] == "ok"


def test_notebook_exercise_grades_as_script(session, content):
    exercise = content.exercise("ds.class-average")
    good = grade(exercise, exercise.solution_path.read_text(), executor=session.executor)
    bad = grade(exercise, exercise.starter_path.read_text(), executor=session.executor)
    assert good.passed, good.results or good.output
    assert not bad.passed


def test_ai_calls_leave_the_sandbox_through_the_kernel(session):
    seen = []

    def handler(kind, payload):
        seen.append((kind, payload))
        if kind == "chat":
            return {"text": "hi from the model", "provider": "ollama", "model": "stub"}
        return {"vectors": [[1.0, 0.0]], "provider": "builtin", "model": "simple_embed"}

    inbox: queue.Queue[dict] = queue.Queue()
    kernel = Kernel(session.container, inbox.put, ai_handler=handler)
    try:
        kernel.execute("import hoss_ai, time\nreply = hoss_ai.chat('hello')\nreply", "a")
        kernel.execute("1 + 1", "b")  # queued while "a" waits for the model
        messages = {"a": [], "b": []}
        done = set()
        while done != {"a", "b"}:
            message = inbox.get(timeout=60)
            if message.get("cell") in messages:
                messages[message["cell"]].append(message)
                if message["type"] == "done":
                    done.add(message["cell"])
        result = next(m for m in messages["a"] if m["type"] == "result")
        assert result["data"]["text/plain"] == "'hi from the model'"
        badge = next(m for m in messages["a"] if m["type"] == "ai")
        assert badge["ok"] is True and badge["provider"] == "ollama" and badge["model"] == "stub"
        assert seen[0][0] == "chat"
        assert seen[0][1]["messages"] == [{"role": "user", "content": "hello"}]
        assert next(m for m in messages["b"] if m["type"] == "result")["data"]["text/plain"] == "2"
    finally:
        kernel.close()


def test_ai_errors_reach_the_learner(session):
    def handler(kind, payload):
        raise RuntimeError("Ollama isn't running")

    inbox: queue.Queue[dict] = queue.Queue()
    kernel = Kernel(session.container, inbox.put, ai_handler=handler)
    try:
        kernel.execute("import hoss_ai\nhoss_ai.chat('hello')", "a")
        messages = []
        while (message := inbox.get(timeout=60))["type"] != "done":
            messages.append(message)
        error = next(m for m in messages if m["type"] == "error")
        assert error["ename"] == "AIError" and "Ollama" in error["evalue"]
    finally:
        kernel.close()
