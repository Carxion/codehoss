"""Copied into every grading run as conftest.py.

Gives exercise tests a `run_program` fixture that runs the learner's main.py
with simulated keyboard input and captures what it prints.
"""

import builtins
import runpy
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

MAIN = Path(__file__).parent / "main.py"

# Notebook code may call display(); graded as a plain script, it does nothing.
builtins.display = lambda *args, **kwargs: None


@dataclass
class ProgramResult:
    out: str
    vars: dict

    @property
    def lines(self) -> list[str]:
        return self.out.splitlines()

    @property
    def last_line(self) -> str:
        return self.lines[-1] if self.lines else ""


@pytest.fixture(autouse=True)
def practice_ai():
    """Every test starts with hoss_ai in plain practice mode: no transport, no script."""
    try:
        import hoss_ai
    except ImportError:
        yield
        return
    hoss_ai._transport = None
    hoss_ai.fake()
    yield
    hoss_ai.fake()


@pytest.fixture
def run_program(monkeypatch, capsys):
    def _run(inputs=()):
        feed = iter(inputs)

        def fake_input(prompt=""):
            try:
                value = next(feed)
            except StopIteration:
                pytest.fail("Your program asked for more input than the test expected.")
            # Echo like a real terminal, so prompts and answers share a line.
            print(f"{prompt}{value}")
            return value

        monkeypatch.setattr(builtins, "input", fake_input)
        # Every test reruns the program in this one process; start each run with no
        # charts left over from the last.
        if "matplotlib.pyplot" in sys.modules:
            sys.modules["matplotlib.pyplot"].close("all")
        capsys.readouterr()
        namespace = runpy.run_path(str(MAIN), run_name="__main__")
        return ProgramResult(out=capsys.readouterr().out, vars=namespace)

    return _run
