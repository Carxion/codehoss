"""The AI tutor: context, prompt, the leak guard, and the streaming endpoint."""

import json

import pytest
from conftest import REPO
from fastapi.testclient import TestClient

from hoss import tutor
from hoss.ai import AIError, Gateway
from hoss.api import create_app
from hoss.registry import load_content
from hoss.store import Store

SOLUTION = """\
score = int(input("Score: "))
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
else:
    grade = "F"
print("Grade:", grade)
"""
STARTER = 'score = int(input("Score: "))\ngrade = "?"\nprint("Grade:", grade)\n'


@pytest.fixture(scope="module")
def content():
    return load_content(REPO / "content")


def lesson_with(content, module_id, step_type):
    module = content.modules[module_id]
    for lesson in module.lessons:
        for i, step in enumerate(lesson.spec.steps):
            if step.type == step_type:
                return module, lesson, i
    raise LookupError(step_type)


def guarded(text, secret=SOLUTION, allowed=STARTER, chunk=None):
    guard = tutor.LeakGuard(secret, allowed)
    pieces = [text] if chunk is None else [text[i : i + chunk] for i in range(0, len(text), chunk)]
    out = "".join(t for piece in pieces for t in guard.feed(piece)) + "".join(guard.finish())
    return out, guard.redactions


# --- leak guard -------------------------------------------------------------------


def test_prose_passes_through():
    text = "Look at line 2: what should happen when the score is 90 or more?"
    assert guarded(text) == (text, 0)


@pytest.mark.parametrize("chunk", [None, 1, 3, 7])
def test_solution_in_a_code_block_is_hidden(chunk):
    text = 'Sure:\n```python\nif score >= 90:\n    grade = "A"\n```\nGood luck!'
    out, redactions = guarded(text, chunk=chunk)
    assert redactions == 1
    assert 'grade = "A"' not in out and "hidden" in out
    assert out.startswith("Sure:") and out.endswith("Good luck!")


def test_lines_the_learner_already_wrote_are_fine():
    text = 'Your line 1 is fine:\n```\nscore = int(input("Score: "))\n```'
    assert guarded(text) == (text, 0)


def test_a_general_example_is_fine():
    text = "For example:\n```\nif age >= 18:\n    print('adult')\n```"
    assert guarded(text) == (text, 0)


def test_inline_code_with_a_solution_line_is_hidden():
    out, redactions = guarded("Try `elif score >= 80:` next.", chunk=2)
    assert redactions == 1 and "elif" not in out


def test_short_inline_code_passes():
    text = "Use `>=` and `elif`, and check `score`."
    assert guarded(text, chunk=1) == (text, 0)


def test_an_unfinished_block_is_still_checked():
    out, redactions = guarded('```\nif score >= 90:\n    grade = "A"')
    assert redactions == 1 and "score >= 90" not in out


def test_long_solutions_allow_one_line_but_not_two():
    secret = "\n".join(f"value_{i} = compute({i})" for i in range(10))
    one, _ = guarded("```\nvalue_3 = compute(3)\n```", secret=secret, allowed="")
    assert "value_3" in one
    guard = tutor.LeakGuard(secret, "")
    first = "".join(guard.feed("`value_3 = compute(3)` then "))
    second = "".join(guard.feed("`value_4 = compute(4)`")) + "".join(guard.finish())
    assert "value_3" in first and "value_4" not in second


def test_no_secret_means_no_redactions():
    text = "```\nanything = goes\n```"
    assert guarded(text, secret="") == (text, 0)


# --- context and prompt -----------------------------------------------------------


def test_exercise_context_has_the_essentials(content):
    module, lesson, i = lesson_with(content, "python-basics", "exercise")
    exercise = lesson.exercises[lesson.spec.steps[i].ref]
    ctx = tutor.context_for(
        module,
        lesson,
        i,
        code="print('hi')\nx = 1\n",
        feedback={
            "passed": False,
            "results": [{"label": "prints a greeting", "outcome": "failed", "message": "boom"}],
        },
    )
    assert ctx.solution == exercise.solution_path.read_text(encoding="utf-8")
    assert ctx.hints == exercise.spec.hints
    prompt = tutor.system_prompt(ctx)
    assert exercise.spec.prompt in prompt
    assert "  2 | x = 1" in prompt  # numbered, so the tutor can say "line 2"
    assert "failed: prints a greeting" in prompt and "boom" in prompt
    assert "Never write the solution" in prompt


def test_exercise_guide_is_shared_with_the_tutor(content):
    module, lesson, i = lesson_with(content, "python-basics", "exercise")
    exercise = lesson.exercises[lesson.spec.steps[i].ref]
    assert exercise.spec.guide, "the first Python Basics exercise should have a guide"
    ctx = tutor.context_for(module, lesson, i)
    prompt = tutor.system_prompt(ctx)
    assert "<worked_examples_the_learner_can_see>" in prompt
    assert exercise.spec.guide[0].code.strip() in prompt


def test_quoting_the_guide_is_not_a_leak():
    guide = 'score = int(input("Score: "))\nif score >= 90:\n    grade = "A"\n'
    reply = f"Look at the example again:\n```python\n{guide}```\n"
    out, redactions = guarded(reply, allowed=f"{STARTER}\n{guide}")
    assert redactions == 0 and guide in out


def test_quiz_context_never_includes_the_answer(content):
    module, lesson, i = lesson_with(content, "python-basics", "quiz")
    step = lesson.spec.steps[i]
    prompt = tutor.system_prompt(tutor.context_for(module, lesson, i))
    assert step.question in prompt
    assert step.explanation not in prompt or not step.explanation
    assert "Don't say which option is right" in prompt


def test_pseudocode_lessons_tell_the_tutor_the_language(content):
    module, lesson, i = lesson_with(content, "programming-basics", "exercise")
    prompt = tutor.system_prompt(tutor.context_for(module, lesson, i))
    assert "Hoss pseudocode" in prompt and "never Python" in prompt


def test_lab_context_uses_files_and_the_solution_commands(content):
    module, lesson, i = lesson_with(content, "docker", "exercise")
    exercise = lesson.exercises[lesson.spec.steps[i].ref]
    ctx = tutor.context_for(module, lesson, i, lab_files={"notes.txt": "hello"})
    assert "--- notes.txt ---" in ctx.code
    assert (exercise.dir / "solution.sh").read_text(encoding="utf-8").strip() in ctx.solution


def test_trim_messages_starts_with_the_learner():
    messages = [{"role": "assistant", "content": "hi"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(30)
    ]
    trimmed = tutor.trim_messages(messages)
    assert trimmed[0]["role"] == "user" and len(trimmed) <= tutor.MAX_TURNS
    assert trimmed[-1]["content"] == "m29"


# --- endpoint ---------------------------------------------------------------------


class TutorGateway(Gateway):
    """Replies with a scripted answer, in small chunks, and records the prompt."""

    def __init__(self):
        super().__init__(ollama_url="http://127.0.0.1:9")
        self.reply = "Look at line 1."
        self.prompts = []

    def chat_stream(self, settings, system, messages, max_tokens):
        if settings.provider is None:
            raise AIError("Choose an AI model first")
        self.prompts.append((system, messages))
        reply = self.reply
        return iter(["fake-model", *(reply[i : i + 4] for i in range(0, len(reply), 4))])


@pytest.fixture
def gateway():
    return TutorGateway()


@pytest.fixture
def client(content, gateway, tmp_path):
    app = create_app(content, store=Store(tmp_path / "db"), gateway=gateway)
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"username": "ada", "password": "password1"})
        yield client


def ask(client, module_id, lesson, step, question="help?", **extra):
    response = client.post(
        "/api/tutor",
        json={
            "module_id": module_id,
            "lesson": lesson,
            "step": step,
            "messages": [{"role": "user", "content": question}],
            **extra,
        },
    )
    if response.status_code != 200:
        return response.status_code, response.json()
    events = [json.loads(line) for line in response.text.splitlines()]
    return 200, events


def text_of(events):
    return "".join(e["text"] for e in events if e["type"] == "text")


def test_needs_an_ai_model(client, content):
    _, lesson, i = lesson_with(content, "python-basics", "exercise")
    status, events = ask(client, "python-basics", lesson.slug, i)
    assert status == 200 and events[-1]["type"] == "error"
    assert "Choose an AI model" in events[-1]["message"]


def test_streams_a_reply_and_records_it(client, content, gateway):
    client.put("/api/ai/settings", json={"provider": "ollama", "model": "qwen2.5:7b"})
    _, lesson, i = lesson_with(content, "python-basics", "exercise")
    status, events = ask(client, "python-basics", lesson.slug, i, code="x = 1")
    assert events[0] == {"type": "meta", "provider": "ollama", "model": "fake-model"}
    assert text_of(events) == "Look at line 1." and events[-1]["type"] == "done"
    system, messages = gateway.prompts[-1]
    assert "  1 | x = 1" in system and messages == [{"role": "user", "content": "help?"}]
    progress = client.get(f"/api/modules/python-basics/lessons/{lesson.slug}").json()["progress"]
    assert progress[str(i)]["tutor_questions"] == 1


def test_leaked_solution_never_reaches_the_learner(client, content, gateway):
    client.put("/api/ai/settings", json={"provider": "ollama", "model": "qwen2.5:7b"})
    _, lesson, i = lesson_with(content, "python-basics", "exercise")
    solution = lesson.exercises[lesson.spec.steps[i].ref].solution_path.read_text(encoding="utf-8")
    gateway.reply = f"Here you go:\n```python\n{solution}\n```\nDone."
    _, events = ask(client, "python-basics", lesson.slug, i)
    body = [line for line in solution.splitlines() if len(line.strip()) > 10]
    assert body and not any(line in text_of(events) for line in body)
    assert events[-1] == {"type": "done", "redactions": 1}


def test_off_in_solo_projects(client, content):
    client.put("/api/ai/settings", json={"provider": "ollama", "model": "qwen2.5:7b"})
    lesson = content.modules["projects"].lessons[0]
    i = next(i for i, s in enumerate(lesson.spec.steps) if s.type == "exercise")
    client.put(f"/api/modules/projects/lessons/{lesson.slug}/level", json={"level": "solo"})
    status, body = ask(client, "projects", lesson.slug, i)
    assert status == 403 and "Solo" in body["detail"]
    client.put(f"/api/modules/projects/lessons/{lesson.slug}/level", json={"level": "assisted"})
    assert ask(client, "projects", lesson.slug, i)[0] == 200


def test_unknown_step_is_404(client):
    assert ask(client, "python-basics", "01-first-program", 999)[0] == 404
