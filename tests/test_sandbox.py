"""Sandbox security and behaviour. Needs Docker and `hoss build-images`."""

import pytest
from conftest import REPO

from hoss.grader import grade, run_program, run_snippet
from hoss.registry import load_content
from hoss.sandbox import SessionManager, docker_available, image_exists

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        not (docker_available() and image_exists("hoss-python")),
        reason="needs Docker and the hoss-python image (run `hoss build-images`)",
    ),
]


@pytest.fixture(scope="module")
def content():
    return load_content(REPO / "content")


@pytest.fixture(scope="module")
def session(content):
    manager = SessionManager(content)
    session = manager.create("python-basics")
    yield session
    manager.close(session.id)


def run(session, code, inputs=None, timeout=10.0):
    return run_program(code, inputs, executor=session.executor, timeout=timeout)


def test_runs_code_with_input(session):
    result = run(session, 'name = input("Name? ")\nprint("Hi", name)', ["Ada"])
    assert result.returncode == 0
    assert result.stdout == "Name? Hi Ada\n"


def test_input_has_no_stray_carriage_returns(session):
    assert run(session, "print(repr(input()))", ["ab"]).stdout == "'ab'\n"


def test_no_network(session):
    code = "import socket\nsocket.create_connection(('1.1.1.1', 53), timeout=3)"
    result = run(session, code)
    assert result.returncode != 0
    assert "OSError" in result.stderr or "unreachable" in result.stderr


def test_runs_as_unprivileged_user(session):
    assert run(session, "import os\nprint(os.getuid())").stdout.strip() == "1000"


def test_root_filesystem_is_read_only(session):
    result = run(session, "open('/etc/evil', 'w')")
    assert result.returncode != 0
    assert "Read-only file system" in result.stderr or "Permission denied" in result.stderr


def test_workspace_is_writable(session):
    code = "open('notes.txt', 'w').write('hi')\nprint(open('notes.txt').read())"
    assert run(session, code).stdout.strip() == "hi"


def test_runs_are_isolated_from_each_other(session):
    run(session, "open('leftover.txt', 'w').write('x')")
    assert (
        run(session, "import os\nprint(os.path.exists('leftover.txt'))").stdout.strip() == "False"
    )


def test_infinite_loop_is_stopped_and_session_survives(session):
    result = run(session, "while True:\n    pass", timeout=2)
    assert result.timed_out
    assert run(session, "print('still alive')").stdout.strip() == "still alive"


def test_memory_limit(session):
    result = run(session, "data = bytearray(1024 * 1024 * 1024)\nprint('allocated')")
    assert "allocated" not in result.stdout


def test_process_limit(session):
    code = (
        "import subprocess\n"
        "procs = [subprocess.Popen(['sleep', '5']) for _ in range(500)]\n"
        "print('spawned all')"
    )
    result = run(session, code)
    assert "spawned all" not in result.stdout


def test_grading_in_sandbox(session, content):
    exercise = content.exercise("py.hello")
    good = grade(exercise, exercise.solution_path.read_text(), executor=session.executor)
    bad = grade(exercise, exercise.starter_path.read_text(), executor=session.executor)
    assert good.passed
    assert not bad.passed and bad.results


def test_try_it_in_sandbox(session):
    assert run_snippet("x = 2", "assert x == 2", executor=session.executor).passed
    assert not run_snippet("x = 1", "assert x == 2", executor=session.executor).passed
