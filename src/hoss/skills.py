"""Skill map, spaced review and streaks: pure functions over progress and review cards.

- **Review cards.** Passing a quiz, try-it or exercise for the first time makes a card,
  due a day later (three for exercises). Answering it from memory when it's due pushes
  the next review further out (x2.5, or x1.3 if a hint or the tutor helped); getting it
  wrong brings it back the next day. Practising before a card is due doesn't change it.
- **Mastery** of a lesson is the average over its practice steps: 1 for a clean pass,
  less for hints, tutor questions or "Show me", and it fades while reviews are overdue.
  Successful reviews earn back what hints cost.
- **Streaks** count consecutive days with any activity, in the learner's time zone.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

from hoss.models import ExerciseStep, QuizStep, Step, TryItStep
from hoss.registry import Content, LoadedLesson, prerequisite_depths
from hoss.store import ReviewCard, StepProgress

DAY = 86_400.0
FIRST_INTERVAL = {"quiz": 1.0, "try-it": 1.0, "exercise": 3.0}
EASE = 2.5
HINTED_EASE = 1.3
MAX_INTERVAL = 180.0
CALENDAR_DAYS = 84  # twelve weeks on the activity calendar


# --- review cards -----------------------------------------------------------------


def review_kind(lesson: LoadedLesson, step: Step) -> str | None:
    """Which steps become review cards: quizzes, try-its and exercises.

    Project checkpoints (they build on each other) and labs (minutes of setup) don't.
    """
    if isinstance(step, QuizStep | TryItStep):
        return step.type
    if isinstance(step, ExerciseStep) and not lesson.spec.project:
        return None if lesson.exercises[step.ref].is_lab else "exercise"
    return None


def schedule(
    card: ReviewCard | None, module_id: str, ref: str, kind: str, passed: bool, now: float
) -> ReviewCard | None:
    """The card after an answer, or None if nothing changes."""
    if card is None:
        if not passed:
            return None
        first = FIRST_INTERVAL[kind]
        return ReviewCard(module_id, ref, first, now + first * DAY)
    if card.due > now:
        return None  # practising early: the schedule stays as it is
    if passed:
        interval = min(MAX_INTERVAL, card.interval_days * (HINTED_EASE if card.hinted else EASE))
        return replace(card, interval_days=interval, due=now + interval * DAY,
                       reps=card.reps + 1, hinted=False)  # fmt: skip
    forgotten = 1 / EASE  # one clean pass from here brings it back in a day
    if card.interval_days <= forgotten:
        return None  # already marked as forgotten this round
    return replace(card, interval_days=forgotten, due=now, lapses=card.lapses + 1)


def mark_helped(card: ReviewCard | None, now: float) -> ReviewCard | None:
    """A hint or tutor question on a due card: the next interval grows less."""
    if card is None or card.due > now or card.hinted:
        return None
    return replace(card, hinted=True)


def due_cards(content: Content, cards: list[ReviewCard], now: float) -> list[dict]:
    """Cards due now (oldest first), skipping any whose step has since changed."""
    due = []
    for card in sorted(cards, key=lambda c: c.due):
        if card.due > now:
            continue
        found = _step(content, card.module_id, card.step_ref)
        if found is None:
            continue
        module, lesson, index, kind = found
        due.append(
            {
                "module_id": card.module_id,
                "module_title": module.spec.title,
                "lesson": lesson.slug,
                "lesson_title": lesson.spec.title,
                "step": index,
                "kind": kind,
                "title": _step_title(lesson, lesson.spec.steps[index]),
                "overdue_days": round((now - card.due) / DAY, 1),
                "reps": card.reps,
            }
        )
    return due


def _step(content: Content, module_id: str, ref: str):
    module = content.modules.get(module_id)
    slug, _, index = ref.rpartition("/")
    lesson = next((les for les in module.lessons if les.slug == slug), None) if module else None
    if lesson is None or not index.isdigit() or int(index) >= len(lesson.spec.steps):
        return None
    kind = review_kind(lesson, lesson.spec.steps[int(index)])
    return (module, lesson, int(index), kind) if kind else None


def _step_title(lesson: LoadedLesson, step: Step) -> str:
    if isinstance(step, QuizStep):
        return step.question
    if isinstance(step, TryItStep):
        return step.prompt.split("\n")[0]
    if isinstance(step, ExerciseStep):
        return lesson.exercises[step.ref].spec.title
    return ""


# --- mastery ----------------------------------------------------------------------


def step_score(progress: StepProgress | None, card: ReviewCard | None, now: float) -> float:
    if progress is None or not progress.done:
        return 0.0
    if progress.showed_solution:
        score = 0.4
    else:
        score = (
            1.0 - min(0.4, 0.12 * progress.hints_used) - min(0.15, 0.05 * progress.tutor_questions)
        )
    if card is not None:
        score = max(score, min(1.0, 0.6 + 0.2 * card.reps))  # remembered without help
        score *= freshness(card, now)
    return round(max(score, 0.2), 3)


def freshness(card: ReviewCard, now: float) -> float:
    """1 until a review is due, then fading to 0.5 as it gets more overdue."""
    overdue = (now - card.due) / DAY
    if overdue <= 0:
        return 1.0
    return max(0.5, 1.0 - 0.25 * overdue / max(card.interval_days, 1.0))


def lesson_skill(
    module_id: str,
    lesson: LoadedLesson,
    progress: dict[str, StepProgress],
    cards: dict[tuple[str, str], ReviewCard],
    now: float,
) -> dict:
    scores, due = [], 0
    started = False
    for index, step in enumerate(lesson.spec.steps):
        ref = f"{lesson.slug}/{index}"
        p = progress.get(ref)
        started = started or bool(p and (p.done or p.attempts))
        if review_kind(lesson, step) is None and not isinstance(step, ExerciseStep):
            continue
        card = cards.get((module_id, ref))
        scores.append(step_score(p, card, now))
        due += bool(card and card.due <= now)
    if scores:
        mastery = sum(scores) / len(scores)
    else:
        refs = [f"{lesson.slug}/{i}" for i in range(len(lesson.spec.steps))]
        mastery = sum(bool((p := progress.get(r)) and p.done) for r in refs) / len(refs)
    if not started:
        state = "new"
    elif due:
        state = "fading"
    elif mastery >= 0.85:
        state = "strong"
    elif mastery >= 0.5:
        state = "practising"
    else:
        state = "learning"
    return {
        "slug": lesson.slug,
        "title": lesson.spec.title,
        "mastery": round(mastery, 3),
        "state": state,
        "due": due,
        "practice": len(scores),
        "practised": sum(s > 0 for s in scores),
    }


def skill_map(
    content: Content,
    progress: dict[str, dict[str, StepProgress]],
    cards: list[ReviewCard],
    now: float,
) -> list[dict]:
    """Every module (with prerequisite depth for layout) and its lessons' mastery."""
    by_key = {(c.module_id, c.step_ref): c for c in cards}
    depths = prerequisite_depths(content.modules)
    modules = []
    for module in content.modules.values():
        lessons = [
            lesson_skill(module.spec.id, lesson, progress.get(module.spec.id, {}), by_key, now)
            for lesson in module.lessons
        ]
        modules.append(
            {
                "id": module.spec.id,
                "title": module.spec.title,
                "level": module.spec.level,
                "depth": depths[module.spec.id],
                "prerequisites": [p for p in module.spec.prerequisites if p in content.modules],
                "mastery": round(sum(les["mastery"] for les in lessons) / len(lessons), 3),
                "due": sum(les["due"] for les in lessons),
                "lessons": lessons,
            }
        )
    return modules


# --- streaks ----------------------------------------------------------------------


def local_day(at: float, tz_minutes: int) -> date:
    """The learner's calendar day for a timestamp; tz_minutes is their offset east of UTC."""
    return (datetime.fromtimestamp(at, UTC) + timedelta(minutes=tz_minutes)).date()


def streaks(times: list[float], now: float, tz_minutes: int = 0) -> dict:
    counts = Counter(local_day(at, tz_minutes) for at in times)
    today = local_day(now, tz_minutes)
    # Today without activity yet doesn't break the streak: it's still going from yesterday.
    day = today if today in counts else today - timedelta(days=1)
    current = 0
    while day in counts:
        current += 1
        day -= timedelta(days=1)
    best = run = 0
    previous = None
    for day in sorted(counts):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return {
        "current": current,
        "best": best,
        "today": today in counts,
        "calendar": [
            {"date": (d := today - timedelta(days=i)).isoformat(), "count": counts.get(d, 0)}
            for i in range(CALENDAR_DAYS - 1, -1, -1)
        ],
    }
