import pytest
from pydantic import ValidationError

from dojo.models import Lesson, Module


def test_module_requires_slug_id():
    with pytest.raises(ValidationError):
        Module.model_validate(
            {
                "id": "Bad Id",
                "title": "x",
                "level": "x",
                "sandbox": {"image": "i"},
                "lessons": ["a"],
            }
        )


def test_module_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="Extra inputs"):
        Module.model_validate(
            {
                "id": "ok",
                "title": "x",
                "level": "x",
                "sandbox": {"image": "i"},
                "lessons": ["a"],
                "lesons": ["typo"],
            }
        )


def test_lesson_parses_each_step_type():
    lesson = Lesson.model_validate(
        {
            "title": "t",
            "steps": [
                {"type": "explain", "md": "hi"},
                {"type": "example", "code": "print(1)"},
                {"type": "try-it", "prompt": "p", "solution": "x=1", "check": "x", "hints": ["h"]},
                {"type": "exercise", "ref": "ex01"},
                {"type": "quiz", "question": "q", "options": ["a", "b"], "answer": 0},
            ],
        }
    )
    assert [s.type for s in lesson.steps] == ["explain", "example", "try-it", "exercise", "quiz"]


def test_quiz_answer_must_be_a_valid_option():
    with pytest.raises(ValidationError, match="not a valid option"):
        Lesson.model_validate(
            {
                "title": "t",
                "steps": [{"type": "quiz", "question": "q", "options": ["a", "b"], "answer": 2}],
            }
        )


def test_unknown_step_type_is_rejected():
    with pytest.raises(ValidationError):
        Lesson.model_validate({"title": "t", "steps": [{"type": "video", "url": "x"}]})
