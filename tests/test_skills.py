"""Spaced review, mastery and streaks (hoss.skills), and their API."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from conftest import REPO
from fastapi.testclient import TestClient

from hoss import skills
from hoss.api import create_app
from hoss.registry import load_content
from hoss.skills import DAY
from hoss.store import ReviewCard, StepProgress, Store

NOW = datetime(2026, 11, 10, 18, 0, tzinfo=UTC).timestamp()


@pytest.fixture(scope="module")
def content():
    return load_content(REPO / "content")


# --- scheduling -------------------------------------------------------------------


def test_first_pass_makes_a_card_due_tomorrow():
    assert skills.schedule(None, "m", "l/1", "quiz", False, NOW) is None
    card = skills.schedule(None, "m", "l/1", "quiz", True, NOW)
    assert card.interval_days == 1 and card.due == NOW + DAY
    assert skills.schedule(None, "m", "l/2", "exercise", True, NOW).interval_days == 3


def test_practising_early_changes_nothing():
    card = ReviewCard("m", "l/1", 1, NOW + DAY)
    assert skills.schedule(card, "m", "l/1", "quiz", True, NOW) is None
    assert skills.schedule(card, "m", "l/1", "quiz", False, NOW) is None


def test_remembering_grows_the_interval_less_with_help():
    card = ReviewCard("m", "l/1", 2, NOW - 10)
    clean = skills.schedule(card, "m", "l/1", "quiz", True, NOW)
    assert clean.interval_days == 5 and clean.reps == 1 and clean.due == NOW + 5 * DAY
    helped = skills.mark_helped(card, NOW)
    assert helped.hinted and skills.mark_helped(helped, NOW) is None
    after = skills.schedule(helped, "m", "l/1", "quiz", True, NOW)
    assert after.interval_days == pytest.approx(2.6) and not after.hinted
    long = ReviewCard("m", "l/1", 150, NOW - 10)
    assert skills.schedule(long, "m", "l/1", "quiz", True, NOW).interval_days == skills.MAX_INTERVAL


def test_forgetting_brings_it_back_tomorrow():
    card = ReviewCard("m", "l/1", 10, NOW - 10)
    forgot = skills.schedule(card, "m", "l/1", "quiz", False, NOW)
    assert forgot.lapses == 1 and forgot.due == NOW
    assert skills.schedule(forgot, "m", "l/1", "quiz", False, NOW + 5) is None  # once a round
    back = skills.schedule(forgot, "m", "l/1", "quiz", True, NOW + 60)
    assert back.interval_days == pytest.approx(1) and back.due == pytest.approx(NOW + 60 + DAY)


def test_help_on_a_card_not_due_is_ignored():
    assert skills.mark_helped(ReviewCard("m", "l/1", 1, NOW + 5), NOW) is None
    assert skills.mark_helped(None, NOW) is None


def test_what_becomes_a_card(content):
    kinds = set()
    for module in content.modules.values():
        for lesson in module.lessons:
            for step in lesson.spec.steps:
                kind = skills.review_kind(lesson, step)
                kinds.add(kind)
                if lesson.spec.project or step.type in ("explain", "example", "showcase"):
                    assert kind is None
                if step.type == "exercise" and kind:
                    assert not lesson.exercises[step.ref].is_lab
    assert {"quiz", "try-it", "exercise"} <= kinds


def test_due_cards_skip_steps_that_no_longer_exist(content):
    lesson = content.modules["python-basics"].lessons[0]
    index = next(i for i, s in enumerate(lesson.spec.steps) if skills.review_kind(lesson, s))
    cards = [
        ReviewCard("python-basics", f"{lesson.slug}/{index}", 1, NOW - DAY),
        ReviewCard("python-basics", f"{lesson.slug}/999", 1, NOW - DAY),
        ReviewCard("gone", "x/1", 1, NOW - DAY),
        ReviewCard("python-basics", f"{lesson.slug}/{index}", 1, NOW + DAY),
    ]
    due = skills.due_cards(content, cards, NOW)
    assert len(due) == 1 and due[0]["lesson_title"] == lesson.spec.title
    assert due[0]["overdue_days"] == 1 and due[0]["title"]


# --- mastery ----------------------------------------------------------------------


def test_step_scores():
    clean = StepProgress(done=True, attempts=1, hints_used=0, showed_solution=False)
    assert skills.step_score(None, None, NOW) == 0
    assert skills.step_score(replace(clean, done=False), None, NOW) == 0
    assert skills.step_score(clean, None, NOW) == 1
    assert skills.step_score(replace(clean, hints_used=2), None, NOW) == pytest.approx(0.76)
    assert skills.step_score(replace(clean, showed_solution=True), None, NOW) == 0.4
    # reviews earn it back, overdue reviews fade it
    shown = replace(clean, showed_solution=True)
    assert skills.step_score(shown, ReviewCard("m", "r", 5, NOW + DAY, reps=2), NOW) == 1
    overdue = ReviewCard("m", "r", 2, NOW - 4 * DAY)
    assert skills.step_score(clean, overdue, NOW) == 0.5


def test_lesson_states(content):
    module = content.modules["python-basics"]
    lesson = module.lessons[0]
    practice = [i for i, s in enumerate(lesson.spec.steps) if skills.review_kind(lesson, s)]
    assert skills.lesson_skill("python-basics", lesson, {}, {}, NOW)["state"] == "new"
    done = StepProgress(True, 1, 0, False)
    all_done = {f"{lesson.slug}/{i}": done for i in range(len(lesson.spec.steps))}
    strong = skills.lesson_skill("python-basics", lesson, all_done, {}, NOW)
    assert strong["state"] == "strong" and strong["mastery"] == 1
    assert strong["practised"] == strong["practice"] > 0
    ref = f"{lesson.slug}/{practice[0]}"
    cards = {("python-basics", ref): ReviewCard("python-basics", ref, 1, NOW - DAY)}
    fading = skills.lesson_skill("python-basics", lesson, all_done, cards, NOW)
    assert fading["state"] == "fading" and fading["due"] == 1
    some = {f"{lesson.slug}/{practice[0]}": StepProgress(False, 2, 0, False)}
    assert skills.lesson_skill("python-basics", lesson, some, {}, NOW)["state"] == "learning"


def test_skill_map_has_depths_and_prerequisites(content):
    modules = {m["id"]: m for m in skills.skill_map(content, {}, [], NOW)}
    assert modules["programming-basics"]["depth"] == 0
    for m in modules.values():
        for p in m["prerequisites"]:
            assert modules[p]["depth"] < m["depth"]
        assert m["mastery"] == 0 and all(les["state"] == "new" for les in m["lessons"])


# --- streaks ----------------------------------------------------------------------


def test_streaks():
    days_ago = [0, 1, 2, 5, 6, 7, 8]
    times = [NOW - d * DAY for d in days_ago]
    result = skills.streaks(times, NOW)
    assert result["current"] == 3 and result["best"] == 4 and result["today"]
    assert len(result["calendar"]) == skills.CALENDAR_DAYS
    assert result["calendar"][-1] == {"date": "2026-11-10", "count": 1}


def test_a_day_without_activity_yet_keeps_the_streak():
    result = skills.streaks([NOW - DAY, NOW - 2 * DAY], NOW)
    assert result["current"] == 2 and not result["today"]
    assert skills.streaks([NOW - 3 * DAY], NOW)["current"] == 0


def test_streaks_use_the_learners_time_zone():
    # 18:00 UTC and 03:00 UTC the next morning: one evening in Denver (UTC-7)...
    times = [NOW, NOW + 9 * 3600]
    assert skills.streaks(times, NOW + 9 * 3600, tz_minutes=-420)["current"] == 1
    # ...but two days in UTC.
    assert skills.streaks(times, NOW + 9 * 3600, tz_minutes=0)["current"] == 2


# --- API --------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "db")


@pytest.fixture
def client(content, store):
    with TestClient(create_app(content, store=store)) as client:
        client.post("/api/auth/register", json={"username": "ada", "password": "password1"})
        yield client


def quiz(content):
    for lesson in content.modules["python-basics"].lessons:
        for i, step in enumerate(lesson.spec.steps):
            if step.type == "quiz":
                return lesson, i, step
    raise LookupError


def answer(client, lesson, i, option):
    url = f"/api/modules/python-basics/lessons/{lesson.slug}/steps/{i}/answer"
    return client.post(url, json={"answer": option}).json()


def make_due(store, ref):
    user = store.authenticate("ada", "password1")
    card = store.review_card(user, "python-basics", ref)
    store.save_review_card(user, replace(card, due=card.due - 2 * DAY))
    return user


def test_quiz_review_cycle(client, content, store):
    lesson, i, step = quiz(content)
    ref = f"{lesson.slug}/{i}"
    wrong = (step.answer + 1) % len(step.options)
    answer(client, lesson, i, wrong)
    assert client.get("/api/review").json() == []
    answer(client, lesson, i, step.answer)
    assert client.get("/api/review").json() == []  # due tomorrow
    user = make_due(store, ref)
    due = client.get("/api/review").json()
    assert [(d["lesson"], d["step"], d["kind"]) for d in due] == [(lesson.slug, i, "quiz")]
    assert client.get("/api/skills").json()["reviews_due"] == 1
    answer(client, lesson, i, step.answer)
    card = store.review_card(user, "python-basics", ref)
    assert card.reps == 1 and card.interval_days == 2.5
    assert client.get("/api/review").json() == []


def test_hints_on_a_due_card_slow_it_down(client, content, store):
    lesson = content.modules["python-basics"].lessons[0]
    i = next(i for i, s in enumerate(lesson.spec.steps) if s.type == "try-it")
    user = store.authenticate("ada", "password1")
    ref = f"{lesson.slug}/{i}"
    store.save_review_card(user, ReviewCard("python-basics", ref, 2, NOW - DAY))
    client.get(f"/api/modules/python-basics/lessons/{lesson.slug}/steps/{i}/hints/1")
    assert store.review_card(user, "python-basics", ref).hinted
    hints = len(lesson.spec.steps[i].hints)
    client.get(f"/api/modules/python-basics/lessons/{lesson.slug}/steps/{i}/hints/{hints + 1}")
    card = store.review_card(user, "python-basics", ref)
    assert card.lapses == 1 and card.interval_days < 1  # "Show me" counts as forgotten


def test_skills_endpoint(client, content):
    lesson, i, step = quiz(content)
    answer(client, lesson, i, step.answer)
    data = client.get("/api/skills?tz=-420").json()
    assert data["streak"]["current"] == 1 and data["streak"]["today"]
    basics = next(m for m in data["modules"] if m["id"] == "python-basics")
    skill = next(les for les in basics["lessons"] if les["slug"] == lesson.slug)
    assert skill["state"] != "new" and skill["mastery"] > 0
