"""Authoring: edit course content with live validation, preview and scaffolding.

Used by the Studio page (authors only, see `is_author`) and `dojo new`. Everything
works on paths relative to the content folder, and only on text files authors write
(YAML, Markdown, code, tests), never datasets or anything outside the folder.

Previews never touch the real content: the module is copied (text files only) into a
temporary folder, the unsaved file is written over its copy, and the copy is loaded
with the normal loader. So a preview shows exactly what saving would give, including
every problem, without learners ever seeing a half-edited lesson.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import tempfile
from collections.abc import Iterator
from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath

import yaml

from dojo.executors import Executor
from dojo.models import TryItStep
from dojo.registry import Content, LoadedLesson, LoadedModule, Problem, _load_module, load_content
from dojo.validate import _check_execution, _check_exercise_refs

TEXT_SUFFIXES = {".yaml", ".yml", ".md", ".py", ".pseudo", ".sh", ".txt", ".json", ".toml", ".cfg"}
TEXT_NAMES = {"Dockerfile", ".dockerignore", ".gitignore", ".gitlab-ci.yml"}
MAX_FILE_BYTES = 200_000
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class AuthoringError(ValueError):
    """A problem the author can fix; the message is shown as-is."""


def is_author(username: str, authors: str | None = None) -> bool:
    """Authors are listed in DOJO_AUTHORS (comma-separated usernames, or * for all)."""
    names = {n.strip().lower() for n in (authors or os.environ.get("DOJO_AUTHORS", "")).split(",")}
    return "*" in names or username.lower() in names


def editable(path: str) -> bool:
    name = PurePosixPath(path).name
    return name in TEXT_NAMES or PurePosixPath(path).suffix in TEXT_SUFFIXES


def resolve(root: Path, path: str) -> Path:
    """A content-relative path, checked: inside the folder and an editable text file."""
    clean = PurePosixPath(path.replace("\\", "/"))
    if not path or clean.is_absolute() or ".." in clean.parts or "\x00" in path:
        raise AuthoringError(f"Not a content path: {path!r}")
    if not editable(path):
        raise AuthoringError(f"Only text files can be edited here: {path}")
    full = (root / clean).resolve()
    if not full.is_relative_to(root.resolve()):
        raise AuthoringError(f"Not a content path: {path!r}")
    return full


# --- browsing ---------------------------------------------------------------------


def tree(root: Path) -> list[dict]:
    """Every module folder and its editable files, for the Studio's file list."""
    modules = []
    for module_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if module_dir.name.startswith((".", "_")) or not (module_dir / "module.yaml").exists():
            continue
        files = sorted(
            p.relative_to(root).as_posix()
            for p in module_dir.rglob("*")
            if p.is_file()
            and editable(p.name)
            and p.stat().st_size <= MAX_FILE_BYTES
            and "__pycache__" not in p.parts
        )
        modules.append({"id": module_dir.name, "files": files})
    return modules


def read(root: Path, path: str) -> str:
    full = resolve(root, path)
    if not full.is_file():
        raise AuthoringError(f"No such file: {path}")
    return full.read_text(encoding="utf-8")


def write(root: Path, path: str, text: str) -> None:
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise AuthoringError(f"That file is too big for the Studio (max {MAX_FILE_BYTES:,} bytes).")
    full = resolve(root, path)
    if len(PurePosixPath(path).parts) < 2:
        raise AuthoringError("Files go inside a module folder.")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(text.encode("utf-8"))  # always LF, whatever the platform


def reload(content: Content) -> list[Problem]:
    """Reload content in place after a save (the app and sessions share this object).

    A module that no longer loads keeps its last good version, so learners never see
    it vanish mid-edit; the problems are returned for the author.
    """
    fresh = load_content(content.root)
    modules = dict(fresh.modules)
    for module_id, old in content.modules.items():
        modules.setdefault(module_id, old)
    content.modules = {k: modules[k] for k in [*fresh.modules, *modules] if k in modules}
    content.problems = fresh.problems
    return fresh.problems


# --- preview ----------------------------------------------------------------------


@dataclass
class Marker:
    """A problem, pinned to a file and line when it can be."""

    level: str
    path: str
    line: int | None
    message: str


@contextlib.contextmanager
def overlay(root: Path, path: str, text: str) -> Iterator[tuple[Content, LoadedModule | None]]:
    """The module containing `path`, loaded from a temporary copy with `text` in place."""
    resolve(root, path)
    module_id = PurePosixPath(path).parts[0]
    source = root / module_id
    if not (source / "module.yaml").exists() and PurePosixPath(path).name != "module.yaml":
        raise AuthoringError(f"No module folder {module_id}/ (it needs a module.yaml).")
    with tempfile.TemporaryDirectory(prefix="dojo-preview-") as tmp:
        temp_root = Path(tmp)
        if source.is_dir():
            # Text files only: datasets and big files aren't needed to load or test.
            shutil.copytree(
                source,
                temp_root / module_id,
                ignore=lambda d, names: [
                    n
                    for n in names
                    if (Path(d) / n).is_file()
                    and (not editable(n) or (Path(d) / n).stat().st_size > MAX_FILE_BYTES)
                ],
            )
        target = temp_root / PurePosixPath(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        temp = Content(root=temp_root)
        module = _load_module(temp_root / module_id, temp)
        if module is not None and module.data_dir and not module.data_dir.exists():
            module.data_dir.mkdir(parents=True)  # data isn't copied; its folder is enough
        temp.problems = [p for p in temp.problems if "sandbox.data folder" not in p.message]
        yield temp, module


def preview(root: Path, path: str, text: str) -> dict:
    """What saving `text` to `path` would give: problems (with lines) and the lesson."""
    from dojo.api import _public_step  # the exact JSON the lesson page renders

    with overlay(root, path, text) as (temp, module):
        problems = list(temp.problems)
        lesson = _lesson_for(module, path)
        if module is not None:
            for les in module.lessons:
                problems += _check_exercise_refs(module, les)
        result: dict = {
            "markers": [asdict(m) for m in markers(problems, {path: text}, root=temp.root)],
            "module": None,
            "lesson": None,
        }
        if module is not None:
            result["module"] = {
                "id": module.spec.id,
                "title": module.spec.title,
                "language": module.spec.language,
                "view": module.spec.default_view,
                "lessons": [les.slug for les in module.lessons],
            }
        if lesson is not None:
            steps = []
            for i, step in enumerate(lesson.spec.steps):
                try:
                    steps.append(_public_step(lesson, i, step))
                except (KeyError, OSError):
                    steps.append({"index": i, "type": "missing", "ref": getattr(step, "ref", "")})
            result["lesson"] = {
                "slug": lesson.slug,
                "title": lesson.spec.title,
                "summary": lesson.spec.summary,
                "steps": steps,
            }
        return result


def test_lesson(root: Path, path: str, text: str, executor: Executor) -> dict:
    """Run the lesson's try-its and exercises (with `text` unsaved) in a sandbox: every
    solution must pass and every starter must fail."""
    with overlay(root, path, text) as (temp, module):
        lesson = _lesson_for(module, path)
        if module is None or lesson is None:
            raise AuthoringError("Open a file inside a lesson to test it.")
        temp.modules = {module.spec.id: replace(module, lessons=[lesson])}
        checks = sum(isinstance(s, TryItStep) for s in lesson.spec.steps) + len(lesson.exercises)
        problems = _check_execution(temp, {module.spec.id: executor})
        return {
            "checks": checks,
            "markers": [asdict(m) for m in markers(problems, {path: text}, root=temp.root)],
        }


def _lesson_for(module: LoadedModule | None, path: str) -> LoadedLesson | None:
    parts = PurePosixPath(path).parts
    if module is None or len(parts) < 3:
        return None
    return next((les for les in module.lessons if les.slug == parts[1]), None)


def markers(problems: list[Problem], texts: dict[str, str], root: Path) -> list[Marker]:
    """Problems with file and line: YAML errors carry a line; schema errors carry a
    location like `steps.3.md`, found in the file's YAML tree."""
    found = []
    for problem in problems:
        where, _, loc = problem.where.partition(" [")
        loc = loc.rstrip("]")
        # YAML errors name the (temporary) file they read; the marker already says which.
        message = re.sub(r'\n?\s*in "[^"]*",', "", problem.message)
        line = None
        text = texts.get(where)
        if text is None and (root / where).is_file():
            text = (root / where).read_text(encoding="utf-8")
        if text is not None:
            if match := re.search(r"line (\d+)", message):
                line = int(match.group(1))
            elif loc:
                line = locate(text, loc.split("."))
            elif (name := re.search(r"'([^']+)'", message)) and name.group(1) in text:
                # e.g. "refers to missing folder 'ex09-x'": point at where it's written
                line = text[: text.index(name.group(1))].count("\n") + 1
        found.append(Marker(problem.level, where, line, message + (f" ({loc})" if loc else "")))
    return found


def locate(text: str, loc: list[str]) -> int | None:
    """1-based line of a pydantic location (e.g. ["steps", "3", "md"]) in YAML text."""
    try:
        node = yaml.compose(text)
    except yaml.YAMLError:
        return None
    line = node.start_mark.line + 1 if node else None
    for i, key in enumerate(loc):
        if isinstance(node, yaml.MappingNode):
            match = next((v for k, v in node.value if k.value == key), None)
            if match is None:
                if i == len(loc) - 1:
                    return line  # a missing field: point at the mapping that should have it
                continue  # a union member's name ("explain"), not a key in the file
            node = match
        elif isinstance(node, yaml.SequenceNode) and key.isdigit() and int(key) < len(node.value):
            node = node.value[int(key)]
        else:
            continue  # pydantic adds names for union members ("explain", "function-after")
        line = node.start_mark.line + 1
    return line


# --- scaffolding ------------------------------------------------------------------


def new_module(root: Path, module_id: str, title: str, language: str = "python") -> list[str]:
    _check_slug(module_id)
    if (root / module_id).exists():
        raise AuthoringError(f"There's already a folder {module_id}/")
    write(
        root,
        f"{module_id}/module.yaml",
        f"id: {module_id}\n"
        f"title: {title}\n"
        "description: One or two sentences on what learners will be able to do.\n"
        "level: beginner\n"
        + (f"language: {language}\n" if language != "python" else "")
        + "sandbox:\n  image: dojo-python\n"
        "lessons:\n  - 01-first-lesson\n",
    )
    return [
        f"{module_id}/module.yaml",
        *_lesson_files(root, module_id, "01-first-lesson", "First lesson"),
    ]


def new_lesson(root: Path, module_id: str, slug: str, title: str) -> list[str]:
    _check_slug(slug)
    module_yaml = f"{module_id}/module.yaml"
    text = read(root, module_yaml)
    if (root / module_id / slug).exists():
        raise AuthoringError(f"There's already a folder {module_id}/{slug}/")
    block = re.search(r"^lessons:[ \t]*\n((?:[ \t]+-[^\n]*\n?)+)", text, re.MULTILINE)
    if block is None:
        raise AuthoringError(
            f"Couldn't find the lessons list in {module_yaml}; add '{slug}' there yourself."
        )
    indent = re.match(r"[ \t]+", block.group(1)).group(0)
    end = block.end(1)
    item = ("" if text[:end].endswith("\n") else "\n") + f"{indent}- {slug}\n"
    write(root, module_yaml, text[:end] + item + text[end:])
    return [module_yaml, *_lesson_files(root, module_id, slug, title)]


def new_exercise(root: Path, module_id: str, lesson: str, slug: str, title: str) -> list[str]:
    _check_slug(slug)
    module = yaml.safe_load(read(root, f"{module_id}/module.yaml")) or {}
    pseudo = module.get("language") == "pseudo"
    lesson_yaml = f"{module_id}/{lesson}/lesson.yaml"
    text = read(root, lesson_yaml)
    folder = f"{module_id}/{lesson}/{slug}"
    if (root / folder).exists():
        raise AuthoringError(f"There's already a folder {folder}/")
    write(root, lesson_yaml, _append_step(text, f"type: exercise\nref: {slug}"))
    ext = ".pseudo" if pseudo else ".py"
    files = {
        f"{folder}/exercise.yaml": (
            f"id: {module_id}.{slug}\n"
            f"title: {title}\n"
            "prompt: |\n  What should the learner build? Say exactly what to print or return.\n"
            "difficulty: 1\n"
            "hints:\n  - A gentle nudge towards the idea.\n  - A more specific hint.\n"
            "  - Nearly the answer, without the code.\n"
        ),
        f"{folder}/starter{ext}": (
            "# TODO: ask for a name and greet them\n"
            if pseudo
            else '# TODO: ask for a name and greet them\nname = "?"\n'
        ),
        f"{folder}/solution{ext}": (
            'name = INPUT("Name: ")\nOUTPUT "Hello, " + name + "!"\n'
            if pseudo
            else 'name = input("Name: ")\nprint(f"Hello, {name}!")\n'
        ),
        f"{folder}/tests/test_visible.py": (
            "def test_greets(run_program):\n"
            '    result = run_program(inputs=["Ada"])\n'
            '    assert "Hello, Ada!" in result.out\n'
        ),
        f"{folder}/tests/test_hidden.py": (
            "import pytest\n\n\n"
            '@pytest.mark.parametrize("name", ["Grace", "Alan Turing"])\n'
            "def test_greets_anyone(run_program, name):\n"
            "    result = run_program(inputs=[name])\n"
            '    assert f"Hello, {name}!" in result.out\n'
        ),
    }
    for path, body in files.items():
        write(root, path, body)
    return [lesson_yaml, *files]


def _lesson_files(root: Path, module_id: str, slug: str, title: str) -> list[str]:
    path = f"{module_id}/{slug}/lesson.yaml"
    write(
        root,
        path,
        f"title: {title}\n"
        "summary: One line on what this lesson teaches.\n"
        "steps:\n"
        "  - type: explain\n"
        "    md: |\n"
        "      Start with *why*: a problem the learner will recognise, then the idea.\n"
        "  - type: quiz\n"
        "    question: A quick check that the idea landed?\n"
        "    options: [The right answer, A tempting wrong one, Another wrong one]\n"
        "    answer: 0\n"
        "    explanation: Why the right answer is right.\n",
    )
    return [path]


def _append_step(text: str, step: str) -> str:
    """Add a step at the end of lesson.yaml's steps list, matching its indentation."""
    try:
        node = yaml.compose(text)
    except yaml.YAMLError as e:
        raise AuthoringError(f"Fix the YAML in lesson.yaml first: {e}") from None
    keys = [k.value for k, _ in node.value] if isinstance(node, yaml.MappingNode) else []
    if not keys or keys[-1] != "steps":
        raise AuthoringError("steps must be the last part of lesson.yaml to add a step here.")
    items = node.value[-1][1].value
    indent = items[0].start_mark.column - 2 if items else 2
    lines = step.splitlines()
    body = "\n".join(
        [" " * indent + "- " + lines[0], *(" " * (indent + 2) + ln for ln in lines[1:])]
    )
    return text.rstrip("\n") + "\n" + body + "\n"


def _check_slug(slug: str) -> None:
    if not SLUG.match(slug):
        raise AuthoringError(
            f"'{slug}' isn't a valid name: use lowercase letters, numbers and dashes."
        )
