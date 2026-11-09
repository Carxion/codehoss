"""Content validation: structure, cross-references, and (optionally) execution.

Execution checks guarantee every exercise and try-it is actually solvable:
the reference solution must pass, and the starter must not.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from importlib import metadata

from dojo.executors import Executor
from dojo.grader import LOCAL, grade, run_snippet
from dojo.models import ExerciseStep, TryItStep
from dojo.registry import Content, LoadedExercise, LoadedLesson, LoadedModule, Problem

# Sandboxes share one container per module, whose pids limit caps parallelism.
SANDBOX_WORKERS = 4


def validate(
    content: Content,
    *,
    run: bool = True,
    executors: dict[str, Executor] | None = None,
) -> list[Problem]:
    """Validate content. `executors` (module id -> executor) runs code in sandboxes."""
    problems = list(content.problems)
    problems += _check_prerequisites(content)
    problems += _check_duplicate_ids(content)
    for module in content.modules.values():
        problems += _check_packages(module)
        for lesson in module.lessons:
            problems += _check_exercise_refs(module, lesson)
    if run:
        problems += _check_execution(content, executors)
    return problems


def _check_prerequisites(content: Content) -> list[Problem]:
    problems = []
    for module in content.modules.values():
        for prereq in module.spec.prerequisites:
            if prereq not in content.modules:
                problems.append(
                    Problem("error", _where(module), f"unknown prerequisite '{prereq}'")
                )

    visiting: set[str] = set()
    done: set[str] = set()

    def visit(module_id: str, path: list[str]) -> None:
        if module_id in done or module_id not in content.modules:
            return
        if module_id in visiting:
            cycle = " -> ".join([*path[path.index(module_id) :], module_id])
            problems.append(Problem("error", "content", f"prerequisite cycle: {cycle}"))
            return
        visiting.add(module_id)
        for prereq in content.modules[module_id].spec.prerequisites:
            visit(prereq, [*path, module_id])
        visiting.discard(module_id)
        done.add(module_id)

    for module_id in content.modules:
        visit(module_id, [])
    return problems


def _check_duplicate_ids(content: Content) -> list[Problem]:
    seen: dict[str, LoadedExercise] = {}
    problems = []
    for ex in content.exercises():
        if ex.spec.id in seen:
            first = seen[ex.spec.id]
            problems.append(
                Problem(
                    "error",
                    _where(ex),
                    f"exercise id '{ex.spec.id}' is already used by {_where(first)}",
                )
            )
        else:
            seen[ex.spec.id] = ex
    return problems


def _check_packages(module: LoadedModule) -> list[Problem]:
    # Stand-in until M1 builds per-module images: check the local environment.
    problems = []
    for package in module.spec.sandbox.packages:
        try:
            metadata.distribution(package)
        except metadata.PackageNotFoundError:
            problems.append(
                Problem("warning", _where(module), f"package '{package}' is not installed locally")
            )
    return problems


def _check_exercise_refs(module: LoadedModule, lesson: LoadedLesson) -> list[Problem]:
    where = f"{module.spec.id}/{lesson.slug}/lesson.yaml"
    refs = {s.ref for s in lesson.spec.steps if isinstance(s, ExerciseStep)}
    problems = [
        Problem("error", where, f"exercise step refers to missing folder '{ref}'")
        for ref in sorted(refs - lesson.exercises.keys())
    ]
    problems += [
        Problem("warning", where, f"exercise '{slug}' is never used in a step")
        for slug in sorted(lesson.exercises.keys() - refs)
    ]
    return problems


def _check_execution(content: Content, executors: dict[str, Executor] | None) -> list[Problem]:
    jobs: list[Callable[[], list[Problem]]] = []
    for module in content.modules.values():
        executor = (executors or {}).get(module.spec.id, LOCAL)
        for lesson in module.lessons:
            for i, step in enumerate(lesson.spec.steps):
                if isinstance(step, TryItStep):
                    where = f"{module.spec.id}/{lesson.slug}/lesson.yaml [steps.{i}]"
                    jobs.append(lambda s=step, w=where, x=executor: _run_try_it(s, w, x))
            for ex in lesson.exercises.values():
                if all(p.exists() for p in ex.required_files):
                    jobs.append(lambda e=ex, x=executor: _run_exercise(e, x))

    workers = SANDBOX_WORKERS if executors else (os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [problem for result in pool.map(lambda job: job(), jobs) for problem in result]


def _run_try_it(step: TryItStep, where: str, executor: Executor) -> list[Problem]:
    problems = []
    solved = run_snippet(step.solution, step.check, executor=executor)
    if not solved.passed:
        problems.append(Problem("error", where, f"solution fails its check: {solved.message}"))
    if run_snippet(step.starter, step.check, executor=executor).passed:
        problems.append(Problem("error", where, "starter already passes the check"))
    return problems


def _run_exercise(ex: LoadedExercise, executor: Executor) -> list[Problem]:
    problems = []
    solution = grade(ex, ex.solution_path.read_text(encoding="utf-8"), executor=executor)
    if solution.timed_out:
        problems.append(Problem("error", _where(ex), "reference solution timed out"))
    elif not solution.passed:
        failing = [f"{r.name}: {r.message}" for r in solution.results if r.outcome != "passed"]
        detail = "; ".join(failing) or solution.output.strip()[-300:]
        problems.append(Problem("error", _where(ex), f"reference solution fails: {detail}"))

    if grade(ex, ex.starter_path.read_text(encoding="utf-8"), executor=executor).passed:
        problems.append(Problem("error", _where(ex), "starter already passes all tests"))
    return problems


def _where(item: LoadedModule | LoadedExercise) -> str:
    if isinstance(item, LoadedModule):
        return f"{item.spec.id}/module.yaml"
    return f"{item.module_id}/{item.lesson_slug}/{item.slug}"
