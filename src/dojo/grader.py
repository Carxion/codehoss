"""Runs learner code against exercise tests and try-it checks.

M0 runs everything as a local subprocess. M1 moves this into a sandboxed
container; the interface (code in, results out) stays the same.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dojo.registry import LoadedExercise

PACKAGE_DIR = Path(__file__).parent
# pytest itself takes a moment to start; don't count that against the learner.
STARTUP_GRACE_S = 10.0


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


def grade(exercise: LoadedExercise, code: str, *, hidden: bool = True) -> GradeResult:
    tests = [exercise.visible_tests]
    if hidden:
        tests.append(exercise.hidden_tests)
    return run_tests(code, tests, timeout=exercise.spec.time_limit_s)


def run_tests(code: str, test_files: list[Path], *, timeout: float) -> GradeResult:
    with tempfile.TemporaryDirectory(prefix="dojo-") as tmp:
        work = Path(tmp)
        (work / "main.py").write_text(code, encoding="utf-8")
        (work / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        shutil.copy(PACKAGE_DIR / "_grader_conftest.py", work / "conftest.py")
        for test_file in test_files:
            shutil.copy(test_file, work / test_file.name)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--junitxml=report.xml",
            # Explicit order so visible tests (the ones learners can read) report first.
            *(test_file.name for test_file in test_files),
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=work,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout + STARTUP_GRACE_S,
                env=_child_env(),
            )
        except subprocess.TimeoutExpired:
            return GradeResult(timed_out=True)

        report = work / "report.xml"
        results = _parse_junit(report) if report.exists() else []
        return GradeResult(results=results, output=proc.stdout + proc.stderr)


def run_snippet(code: str, check: str, *, timeout: float = 5.0) -> SnippetResult:
    with tempfile.TemporaryDirectory(prefix="dojo-") as tmp:
        work = Path(tmp)
        (work / "main.py").write_text(code, encoding="utf-8")
        (work / "check.py").write_text(check, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(PACKAGE_DIR / "_tryit_runner.py"), "main.py", "check.py"],
                cwd=work,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=_child_env(),
            )
        except subprocess.TimeoutExpired:
            return SnippetResult(False, f"Timed out after {timeout:g}s — is there an endless loop?")
        if proc.returncode == 0:
            return SnippetResult(True)
        lines = proc.stderr.strip().splitlines()
        return SnippetResult(False, _clean_message(lines[-1] if lines else "check failed"))


def _parse_junit(report: Path) -> list[TestResult]:
    results = []
    for case in ET.parse(report).getroot().iter("testcase"):
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


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env
