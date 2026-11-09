"""Runs learner code: free runs, exercise tests, and try-it checks.

Every function takes an executor, so the same grading logic works locally
(authoring, `dojo validate`) and inside a sandbox container (the API).
"""

from __future__ import annotations

import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dojo.executors import ExecResult, Executor, LocalExecutor, OutputCallback, StdinFeed
from dojo.registry import LoadedExercise

PACKAGE_DIR = Path(__file__).parent
# pytest itself takes a moment to start; don't count that against the learner.
STARTUP_GRACE_S = 10.0
RUN_TIMEOUT_S = 10.0

LOCAL = LocalExecutor()


@dataclass
class TestResult:
    __test__ = False  # not a pytest test class

    name: str
    outcome: Literal["passed", "failed", "error", "skipped"]
    message: str = ""

    @property
    def label(self) -> str:
        """test_first_line_says_hello -> 'first line says hello'"""
        return self.name.removeprefix("test_").replace("_", " ")


@dataclass
class GradeResult:
    results: list[TestResult] = field(default_factory=list)
    timed_out: bool = False
    output: str = ""

    @property
    def passed(self) -> bool:
        return (
            not self.timed_out
            and bool(self.results)
            and all(r.outcome == "passed" for r in self.results)
        )


@dataclass
class SnippetResult:
    passed: bool
    message: str = ""


def run_program(
    code: str,
    inputs: list[str] | StdinFeed | None = None,
    *,
    executor: Executor = LOCAL,
    timeout: float = RUN_TIMEOUT_S,
    on_output: OutputCallback | None = None,
    cpu_seconds: int | None = None,
    cancel: threading.Event | None = None,
) -> ExecResult:
    """Run learner code as a script.

    `inputs` is either a list of lines typed at input() up front, or a StdinFeed for
    interactive runs where the learner types while the program waits.
    """
    stdin = inputs if isinstance(inputs, StdinFeed) else "".join(f"{x}\n" for x in inputs or [])
    return executor.execute(
        {"main.py": code.encode("utf-8")},
        [executor.python, "-u", "main.py"],
        timeout=timeout,
        stdin=stdin,
        on_output=on_output,
        cpu_seconds=cpu_seconds,
        cancel=cancel,
    )


def grade(
    exercise: LoadedExercise, code: str, *, hidden: bool = True, executor: Executor = LOCAL
) -> GradeResult:
    tests = [exercise.visible_tests]
    if hidden:
        tests.append(exercise.hidden_tests)
    return run_tests(code, tests, timeout=exercise.spec.time_limit_s, executor=executor)


def run_tests(
    code: str, test_files: list[Path], *, timeout: float, executor: Executor = LOCAL
) -> GradeResult:
    files = {
        "main.py": code.encode("utf-8"),
        "pytest.ini": b"[pytest]\n",
        "conftest.py": (PACKAGE_DIR / "_grader_conftest.py").read_bytes(),
        "dojo_checks.py": (PACKAGE_DIR / "_dojo_checks.py").read_bytes(),
        **{test_file.name: test_file.read_bytes() for test_file in test_files},
    }
    argv = [
        executor.python,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--junitxml=report.xml",
        # Explicit order so visible tests (the ones learners can read) report first.
        *(test_file.name for test_file in test_files),
    ]
    result = executor.execute(
        files, argv, timeout=timeout + STARTUP_GRACE_S, collect=("report.xml",)
    )
    if result.timed_out:
        return GradeResult(timed_out=True)
    report = result.files.get("report.xml")
    return GradeResult(
        results=_parse_junit(report) if report else [],
        output=result.stdout + result.stderr,
    )


def run_snippet(
    code: str, check: str, *, timeout: float = 5.0, executor: Executor = LOCAL
) -> SnippetResult:
    files = {
        "main.py": code.encode("utf-8"),
        "check.py": check.encode("utf-8"),
        "_tryit_runner.py": (PACKAGE_DIR / "_tryit_runner.py").read_bytes(),
        "dojo_checks.py": (PACKAGE_DIR / "_dojo_checks.py").read_bytes(),
    }
    argv = [executor.python, "_tryit_runner.py", "main.py", "check.py"]
    result = executor.execute(files, argv, timeout=timeout)
    if result.timed_out:
        return SnippetResult(False, f"Timed out after {timeout:g}s — is there an endless loop?")
    if result.returncode == 0:
        return SnippetResult(True)
    lines = result.stderr.strip().splitlines()
    return SnippetResult(False, _clean_message(lines[-1] if lines else "check failed"))


def _parse_junit(report: bytes) -> list[TestResult]:
    results = []
    for case in ET.fromstring(report).iter("testcase"):
        outcome: Literal["passed", "failed", "error", "skipped"] = "passed"
        message = ""
        for tag, kind in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
            element = case.find(tag)
            if element is not None:
                outcome = kind
                message = _clean_message(element.get("message") or element.text or "")
                break
        results.append(TestResult(case.get("name", "?"), outcome, message))
    return results


def _clean_message(raw: str) -> str:
    first = raw.strip().splitlines()[0] if raw.strip() else ""
    return first.removeprefix("AssertionError: ").removeprefix("Failed: ")
