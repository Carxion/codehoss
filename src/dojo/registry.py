"""Discovers and loads modules from the content directory.

Loading never stops at the first problem: everything that can be parsed is
loaded, and every problem found is collected so authors can fix them in one pass.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from dojo.models import Exercise, Lesson, Module


@dataclass
class Problem:
    level: Literal["error", "warning"]
    where: str
    message: str


@dataclass
class LoadedExercise:
    module_id: str
    lesson_slug: str
    slug: str
    dir: Path
    spec: Exercise

    @property
    def starter_path(self) -> Path:
        return self.dir / "starter.py"

    @property
    def solution_path(self) -> Path:
        return self.dir / "solution.py"

    @property
    def visible_tests(self) -> Path:
        return self.dir / "tests" / "test_visible.py"

    @property
    def hidden_tests(self) -> Path:
        return self.dir / "tests" / "test_hidden.py"

    @property
    def required_files(self) -> list[Path]:
        return [self.starter_path, self.solution_path, self.visible_tests, self.hidden_tests]


@dataclass
class LoadedLesson:
    slug: str
    dir: Path
    spec: Lesson
    exercises: dict[str, LoadedExercise] = field(default_factory=dict)


@dataclass
class LoadedModule:
    dir: Path
    spec: Module
    lessons: list[LoadedLesson] = field(default_factory=list)

    def exercises(self) -> Iterator[LoadedExercise]:
        for lesson in self.lessons:
            yield from lesson.exercises.values()


@dataclass
class Content:
    root: Path
    modules: dict[str, LoadedModule] = field(default_factory=dict)
    problems: list[Problem] = field(default_factory=list)

    def exercises(self) -> Iterator[LoadedExercise]:
        for module in self.modules.values():
            yield from module.exercises()

    def exercise(self, exercise_id: str) -> LoadedExercise | None:
        return next((ex for ex in self.exercises() if ex.spec.id == exercise_id), None)


def load_content(root: Path) -> Content:
    content = Content(root=root)
    for module_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if module_dir.name.startswith((".", "_")) or not (module_dir / "module.yaml").exists():
            continue
        module = _load_module(module_dir, content)
        if module is not None:
            content.modules[module.spec.id] = module
    return content


def _load_module(module_dir: Path, content: Content) -> LoadedModule | None:
    spec = _parse(Module, module_dir / "module.yaml", content)
    if spec is None:
        return None
    where = _rel(module_dir / "module.yaml", content.root)
    if spec.id != module_dir.name:
        content.problems.append(
            Problem("error", where, f"id '{spec.id}' must match folder name '{module_dir.name}'")
        )

    module = LoadedModule(dir=module_dir, spec=spec)
    for slug in spec.lessons:
        lesson_dir = module_dir / slug
        if not (lesson_dir / "lesson.yaml").exists():
            content.problems.append(
                Problem("error", where, f"lesson '{slug}' has no {slug}/lesson.yaml")
            )
            continue
        lesson = _load_lesson(spec.id, lesson_dir, content)
        if lesson is not None:
            module.lessons.append(lesson)

    for lesson_dir in module_dir.iterdir():
        if (lesson_dir / "lesson.yaml").exists() and lesson_dir.name not in spec.lessons:
            content.problems.append(
                Problem("warning", where, f"lesson folder '{lesson_dir.name}' is not listed")
            )
    return module


def _load_lesson(module_id: str, lesson_dir: Path, content: Content) -> LoadedLesson | None:
    spec = _parse(Lesson, lesson_dir / "lesson.yaml", content)
    if spec is None:
        return None
    lesson = LoadedLesson(slug=lesson_dir.name, dir=lesson_dir, spec=spec)
    for ex_dir in sorted(p for p in lesson_dir.iterdir() if (p / "exercise.yaml").exists()):
        ex_spec = _parse(Exercise, ex_dir / "exercise.yaml", content)
        if ex_spec is None:
            continue
        exercise = LoadedExercise(module_id, lesson_dir.name, ex_dir.name, ex_dir, ex_spec)
        for path in exercise.required_files:
            if not path.exists():
                content.problems.append(
                    Problem("error", _rel(ex_dir, content.root), f"missing {_rel(path, ex_dir)}")
                )
        lesson.exercises[ex_dir.name] = exercise
    return lesson


def _parse[M: BaseModel](model: type[M], path: Path, content: Content) -> M | None:
    where = _rel(path, content.root)
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return model.model_validate(data)
    except yaml.YAMLError as e:
        content.problems.append(Problem("error", where, f"invalid YAML: {e}"))
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            content.problems.append(Problem("error", f"{where} [{loc}]", err["msg"]))
    return None


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
