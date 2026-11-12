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

from hoss.models import Exercise, Lesson, Module


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
    language: str = "python"

    @property
    def ext(self) -> str:
        """File extension of starters and solutions: .py, or .pseudo for pseudocode."""
        return ".pseudo" if self.language == "pseudo" else ".py"

    @property
    def is_lab(self) -> bool:
        """Lab exercises have starter files/, a solution/ folder and solution.sh (the
        commands that reach the solved state) instead of starter.py and solution.py."""
        return (self.dir / "files").is_dir()

    @property
    def starter_path(self) -> Path:
        return self.dir / f"starter{self.ext}"

    @property
    def solution_path(self) -> Path:
        return self.dir / f"solution{self.ext}"

    @property
    def visible_tests(self) -> Path:
        return self.dir / "tests" / "test_visible.py"

    @property
    def hidden_tests(self) -> Path:
        return self.dir / "tests" / "test_hidden.py"

    def starter_for(self, level: str) -> Path | None:
        """Starter file for a project level; None means "continue from your own code"."""
        if level == "solo":
            path = self.dir / f"starter.solo{self.ext}"
            return path if path.exists() else None
        if level == "assisted" and (self.dir / f"starter.assisted{self.ext}").exists():
            return self.dir / f"starter.assisted{self.ext}"
        return self.starter_path

    @property
    def variant_starters(self) -> list[Path]:
        return [
            p
            for p in (
                self.dir / f"starter.assisted{self.ext}",
                self.dir / f"starter.solo{self.ext}",
            )
            if p.exists()
        ]

    @property
    def required_files(self) -> list[Path]:
        if self.is_lab:
            return [
                self.dir / "solution",
                self.dir / "solution.sh",
                self.visible_tests,
                self.hidden_tests,
            ]
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
    # Beginner-written notes shown on hover and in the Library Explorer (glossary.yaml).
    glossary: dict[str, str] = field(default_factory=dict)

    @property
    def data_dir(self) -> Path | None:
        return (self.dir / self.spec.sandbox.data).resolve() if self.spec.sandbox.data else None

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
    # Courses are listed in the order they're meant to be taken: those with no
    # prerequisites first, then each course after everything it builds on.
    depth = prerequisite_depths(content.modules)
    content.modules = dict(sorted(content.modules.items(), key=lambda m: (depth[m[0]], m[0])))
    return content


def prerequisite_depths(modules: dict[str, LoadedModule]) -> dict[str, int]:
    """Length of each module's longest prerequisite chain (cycles are reported elsewhere)."""
    depths: dict[str, int] = {}

    def depth(module_id: str, seen: frozenset[str]) -> int:
        if module_id in depths:
            return depths[module_id]
        prereqs = [
            p for p in modules[module_id].spec.prerequisites if p in modules and p not in seen
        ]
        result = 1 + max((depth(p, seen | {module_id}) for p in prereqs), default=-1)
        depths[module_id] = result
        return result

    for module_id in modules:
        depth(module_id, frozenset())
    return depths


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
    if module.data_dir is not None and not module.data_dir.is_dir():
        content.problems.append(
            Problem("error", where, f"sandbox.data folder '{spec.sandbox.data}' does not exist")
        )
    module.glossary = _load_glossary(module_dir / "glossary.yaml", content)
    for slug in spec.lessons:
        lesson_dir = module_dir / slug
        if not (lesson_dir / "lesson.yaml").exists():
            content.problems.append(
                Problem("error", where, f"lesson '{slug}' has no {slug}/lesson.yaml")
            )
            continue
        lesson = _load_lesson(spec.id, lesson_dir, content, spec.language)
        if lesson is not None:
            module.lessons.append(lesson)

    for lesson_dir in module_dir.iterdir():
        if (lesson_dir / "lesson.yaml").exists() and lesson_dir.name not in spec.lessons:
            content.problems.append(
                Problem("warning", where, f"lesson folder '{lesson_dir.name}' is not listed")
            )
    return module


def _load_lesson(
    module_id: str, lesson_dir: Path, content: Content, language: str
) -> LoadedLesson | None:
    spec = _parse(Lesson, lesson_dir / "lesson.yaml", content)
    if spec is None:
        return None
    lesson = LoadedLesson(slug=lesson_dir.name, dir=lesson_dir, spec=spec)
    for ex_dir in sorted(p for p in lesson_dir.iterdir() if (p / "exercise.yaml").exists()):
        ex_spec = _parse(Exercise, ex_dir / "exercise.yaml", content)
        if ex_spec is None:
            continue
        exercise = LoadedExercise(
            module_id, lesson_dir.name, ex_dir.name, ex_dir, ex_spec, language
        )
        for path in exercise.required_files:
            if not path.exists():
                content.problems.append(
                    Problem("error", _rel(ex_dir, content.root), f"missing {_rel(path, ex_dir)}")
                )
        lesson.exercises[ex_dir.name] = exercise
    return lesson


def _load_glossary(path: Path, content: Content) -> dict[str, str]:
    if not path.exists():
        return {}
    where = _rel(path, content.root)
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        content.problems.append(Problem("error", where, f"invalid YAML: {e}"))
        return {}
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        content.problems.append(Problem("error", where, "glossary must map names to text"))
        return {}
    return data


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
