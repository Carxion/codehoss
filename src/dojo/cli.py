"""The `dojo` command-line interface.

The terminal way to work through exercises (the browser IDE in M2 replaces it for
learners), plus authoring and ops commands: validate, build-images, serve.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from dojo.grader import grade
from dojo.registry import Content, LoadedExercise, load_content
from dojo.sandbox import (
    SandboxError,
    SessionManager,
    build_image,
    build_library_index,
    image_specs,
)
from dojo.validate import validate as validate_content

app = typer.Typer(
    help="DataDojo: learn Python, data science and AI by doing.",
    no_args_is_help=True,
    add_completion=False,
)
# Windows consoles often can't encode everything that learner code or docker prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
console = Console()

WORKSPACE = Path("workspace")


def _load() -> Content:
    root = Path(os.environ.get("DOJO_CONTENT", "content")).resolve()
    if not root.is_dir():
        console.print(f"[red]Content folder not found:[/] {root}")
        console.print("Run from the repo root, or set DOJO_CONTENT.")
        raise typer.Exit(2)
    return load_content(root)


def _find(content: Content, exercise_id: str) -> LoadedExercise:
    exercise = content.exercise(exercise_id)
    if exercise is None:
        console.print(f"[red]No exercise with id[/] '{exercise_id}'. Try [bold]dojo list[/].")
        raise typer.Exit(2)
    return exercise


@app.command("list")
def list_cmd() -> None:
    """Show all modules, lessons and exercises."""
    content = _load()
    for module in content.modules.values():
        prereqs = ", ".join(module.spec.prerequisites) or "none"
        tree = Tree(f"[bold]{module.spec.title}[/] [dim]({module.spec.id}, needs: {prereqs})[/]")
        for lesson in module.lessons:
            branch = tree.add(f"{lesson.slug}  {lesson.spec.title}")
            for ex in lesson.exercises.values():
                stars = "*" * ex.spec.difficulty
                branch.add(f"[cyan]{ex.spec.id}[/]  {ex.spec.title} [yellow]{stars}[/]")
        console.print(tree)


@app.command()
def validate(
    run: Annotated[
        bool, typer.Option("--run/--no-run", help="Execute solutions and starters.")
    ] = True,
    sandbox: Annotated[
        bool, typer.Option(help="Run code in the Docker sandboxes learners use.")
    ] = False,
) -> None:
    """Check that all content is well-formed and every exercise is solvable."""
    content = _load()
    manager = SessionManager(content) if sandbox and run else None
    try:
        with console.status("Validating content..."):
            executors = None
            if manager:
                executors = {m: manager.create(m).executor for m in content.modules}
            problems = validate_content(content, run=run, executors=executors)
    except SandboxError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(2) from None
    finally:
        if manager:
            manager.close_all()

    errors = [p for p in problems if p.level == "error"]
    warnings = [p for p in problems if p.level == "warning"]
    for p in errors + warnings:
        colour = "red" if p.level == "error" else "yellow"
        console.print(f"[{colour}]{p.level:7}[/] {p.where}: {p.message}")

    exercises = sum(1 for _ in content.exercises())
    console.print(
        f"\n{len(content.modules)} module(s), {exercises} exercise(s): "
        f"[red]{len(errors)} error(s)[/], [yellow]{len(warnings)} warning(s)[/]"
    )
    if errors:
        raise typer.Exit(1)


@app.command()
def start(
    exercise_id: str,
    reset: Annotated[bool, typer.Option(help="Overwrite your file with a fresh starter.")] = False,
) -> None:
    """Show an exercise and create your starter file in workspace/."""
    exercise = _find(_load(), exercise_id)
    console.print(Panel(Markdown(exercise.spec.prompt), title=exercise.spec.title))

    target = WORKSPACE / f"{exercise_id}.py"
    if target.exists() and not reset:
        console.print(f"Continuing your file: [bold]{target}[/] (use --reset to start over)")
    else:
        WORKSPACE.mkdir(exist_ok=True)
        target.write_text(exercise.starter_path.read_text(encoding="utf-8"), encoding="utf-8")
        console.print(f"Starter created: [bold]{target}[/]")
    console.print(f"When you're ready: [bold]dojo check {exercise_id}[/]")


@app.command()
def check(
    exercise_id: str,
    file: Annotated[Path | None, typer.Argument(help="Defaults to workspace/<id>.py")] = None,
    sandbox: Annotated[
        bool, typer.Option(help="Run inside a Docker sandbox instead of on this machine.")
    ] = False,
) -> None:
    """Run the tests for an exercise against your code."""
    content = _load()
    exercise = _find(content, exercise_id)
    path = file or WORKSPACE / f"{exercise_id}.py"
    if not path.exists():
        console.print(f"[red]{path} not found.[/] Run [bold]dojo start {exercise_id}[/] first.")
        raise typer.Exit(2)

    code = path.read_text(encoding="utf-8")
    if sandbox:
        manager = SessionManager(content)
        with console.status("Starting sandbox and running tests..."):
            try:
                session = manager.create(exercise.module_id)
            except SandboxError as e:
                console.print(f"[red]{e}[/]")
                raise typer.Exit(2) from None
            try:
                result = grade(exercise, code, executor=session.executor)
            finally:
                manager.close(session.id)
    else:
        with console.status("Running tests..."):
            result = grade(exercise, code)

    if result.timed_out:
        console.print("[red]Your program took too long.[/] Is there a loop that never ends?")
        raise typer.Exit(1)

    table = Table(show_header=False, box=None)
    for r in result.results:
        mark = "[green]PASS[/]" if r.outcome == "passed" else "[red]FAIL[/]"
        table.add_row(mark, r.label, f"[dim]{r.message}[/]")
    console.print(table)

    if result.passed:
        console.print(f"\n[bold green]All {len(result.results)} tests passed. Nice work![/]")
        return
    if not result.results:
        console.print(result.output.strip()[-1500:])
    console.print(f"\n[yellow]Hint:[/] {exercise.spec.hints[0]}")
    if len(exercise.spec.hints) > 1:
        console.print(f"[dim]More help: dojo hint {exercise_id} 2[/]")
    raise typer.Exit(1)


@app.command()
def hint(exercise_id: str, level: int = 1) -> None:
    """Show a hint for an exercise. Higher levels give more help."""
    exercise = _find(_load(), exercise_id)
    hints = exercise.spec.hints
    level = max(1, min(level, len(hints)))
    console.print(f"[yellow]Hint {level}/{len(hints)}:[/] {hints[level - 1]}")
    if level < len(hints):
        console.print(f"[dim]More help: dojo hint {exercise_id} {level + 1}[/]")


@app.command("build-images")
def build_images() -> None:
    """Build the Docker sandbox image and Library Explorer index for every module."""
    content = _load()
    try:
        for image, packages in image_specs(content).items():
            console.print(f"[bold]Building {image}[/] with {', '.join(packages)}")
            build_image(image, packages, on_output=lambda line: console.print(f"[dim]{line}[/]"))
            console.print(f"[green]Built {image}[/]")
        for module_id in content.modules:
            path = build_library_index(content, module_id)
            console.print(f"[green]Indexed libraries for {module_id}[/] -> {path}")
    except SandboxError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1) from None


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the server: API under /api, the browser app (web/dist) at /."""
    import uvicorn

    from dojo.api import create_app

    static = Path("web/dist")
    if not static.is_dir():
        console.print(
            "[yellow]web/dist not found: API only. Build the app: cd web && npm run build[/]"
        )
    uvicorn.run(create_app(_load(), static_dir=static), host=host, port=port)
