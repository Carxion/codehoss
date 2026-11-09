"""Schemas for module.yaml, lesson.yaml and exercise.yaml.

See docs/CURRICULUM.md#module-format for the authoring guide.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
EXERCISE_ID = r"^[a-z0-9]+([.-][a-z0-9]+)*$"


class _Strict(BaseModel):
    # Typos in content files should fail validation, not be silently ignored.
    model_config = ConfigDict(extra="forbid")


# --- module.yaml -----------------------------------------------------------


class Sandbox(_Strict):
    image: str
    packages: list[str] = []
    services: list[str] = []
    network: Literal["none"] | list[str] = "none"
    memory: str = Field(default="256m", pattern=r"^\d+[mg]$")
    # Folder (relative to the module) mounted read-only at /data in every session.
    data: str | None = None
    # The module calls AI models (dojo_ai); the UI shows the AI backend picker.
    ai: bool = False


class LibraryExplorer(_Strict):
    featured: list[str] = []  # pinned at the top of the explorer
    modules: list[str] = []  # also indexed, listed below the featured ones


class Module(_Strict):
    id: str = Field(pattern=SLUG)
    title: str
    description: str = ""
    level: str
    prerequisites: list[str] = []
    sandbox: Sandbox
    default_view: Literal["editor", "notebook"] = "editor"
    library_explorer: LibraryExplorer = LibraryExplorer()
    lessons: list[str] = Field(min_length=1)


# --- lesson.yaml -----------------------------------------------------------


class ExplainStep(_Strict):
    type: Literal["explain"]
    md: str


class ExampleStep(_Strict):
    type: Literal["example"]
    code: str
    md: str = ""
    runnable: bool = True


class TryItStep(_Strict):
    """A small typed step, checked instantly.

    `check` runs after the learner's code in the same namespace; printed output
    is available to it as `_output`.
    """

    type: Literal["try-it"]
    prompt: str
    starter: str = ""
    solution: str
    check: str
    hints: list[str] = Field(min_length=1)


# Algorithms the browser can animate (web/src/showcase/algorithms.ts).
SHOWCASES = Literal[
    "linear-search",
    "binary-search",
    "two-pointers",
    "bracket-stack",
    "fib-tree",
    "bubble-sort",
    "insertion-sort",
    "merge-sort",
    "bst-insert",
    "heap",
    "bfs",
    "dfs",
    "dijkstra",
    "coin-change",
]


class ShowcaseStep(_Strict):
    """An animated, step-through visualisation of an algorithm, played in the browser."""

    type: Literal["showcase"]
    algorithm: SHOWCASES
    md: str = ""
    input: dict = {}


class ExerciseStep(_Strict):
    type: Literal["exercise"]
    ref: str


class QuizStep(_Strict):
    type: Literal["quiz"]
    question: str
    options: list[str] = Field(min_length=2)
    answer: int
    explanation: str = ""

    @model_validator(mode="after")
    def _answer_in_range(self) -> QuizStep:
        if not 0 <= self.answer < len(self.options):
            raise ValueError(f"answer {self.answer} is not a valid option index")
        return self


Step = Annotated[
    ExplainStep | ExampleStep | TryItStep | ExerciseStep | QuizStep | ShowcaseStep,
    Field(discriminator="type"),
]


LEVELS = ("guided", "assisted", "solo")


class Project(_Strict):
    """Makes a lesson a multi-checkpoint project (Projects module).

    Each exercise step is a checkpoint whose tests cover everything built so far.
    Learners choose a level: guided (starter.py), assisted (starter.assisted.py, else
    the guided one), solo (starter.solo.py, else they continue from their own code).
    """

    brief: str
    uses: list[str] = []  # modules whose skills it practises (shown as badges)
    view: Literal["editor", "notebook"] | None = None  # overrides the module's view
    ai: bool = False  # shows the AI model picker banner


class Lesson(_Strict):
    title: str
    summary: str = ""
    project: Project | None = None
    steps: list[Step] = Field(min_length=1)


# --- exercise.yaml ---------------------------------------------------------


class Exercise(_Strict):
    id: str = Field(pattern=EXERCISE_ID)
    title: str
    prompt: str
    difficulty: int = Field(ge=1, le=5)
    time_limit_s: float = Field(default=5, gt=0)
    hints: list[str] = Field(min_length=1)
