import json
import sys
from pathlib import Path

import pytest

from dojo import _dojo_pseudo as pseudo
from dojo import grader
from dojo.explain import explain_traceback

PROGRAM = """// every statement once
scores = [72, 95, 58]
total = 0
FOR EACH s IN scores DO
    total = total + s
END FOR
FUNCTION grade(score)
    IF score >= 90 THEN
        RETURN "A"
    ELSE IF score >= 60 THEN
        RETURN "C"
    ELSE
        RETURN "F"
    END IF
END FUNCTION
grades = []
FOR i FROM 0 TO LENGTH(scores) - 1 DO
    APPEND(grades, grade(scores[i]))
END FOR
n = 0
REPEAT
    n = n + 1
UNTIL n == 3
WHILE n > 0 DO
    n = n - 1
END WHILE
person = {"name": "Ada", "age": 36}
person["age"] = person["age"] + 1
OUTPUT "Total:", total, ROUND(total / 3, 1), person
"""


def run(source: str, capsys) -> tuple[str, dict]:
    variables = pseudo.run_source(source)
    return capsys.readouterr().out, variables


def test_runs_every_statement(capsys):
    out, v = run(PROGRAM, capsys)
    assert out == 'Total: 225 75 {"name": "Ada", "age": 37}\n'
    assert v["grades"] == ["C", "A", "F"]
    assert v["n"] == 0
    # Learner functions can be called from Python (exercise tests do this).
    assert v["grade"](91) == "A"


@pytest.mark.parametrize(
    ("expr", "shown"),
    [
        ("7 / 2", "3.5"),
        ("6 / 2", "3"),  # whole results stay whole
        ("7 DIV 2", "3"),
        ("7 MOD 2", "1"),
        ("2 + 3 * 4", "14"),
        ("(2 + 3) * 4", "20"),
        ('"5" + "5"', "55"),
        ("TRUE AND NOT FALSE", "TRUE"),
        ("1 == TRUE", "FALSE"),  # no Python surprises
        ("ROUND(2.5)", "3"),  # half up, not banker's rounding
        ('TO_NUMBER(" 4.50 ")', "4.5"),
        ('CONTAINS("abc", "b")', "TRUE"),
        ("[1, 2] + [3]", "[1, 2, 3]"),
        ('UPPER("hi") + LOWER("YO")', "HIyo"),
    ],
)
def test_expressions(expr, shown, capsys):
    out, _ = run(f"OUTPUT {expr}\n", capsys)
    assert out == f"{shown}\n"


@pytest.mark.parametrize(
    ("source", "line", "fragment"),
    [
        ('x = 5\nOUTPUT "n" + x\n', 2, "TO_TEXT"),
        ("IF x = 5 THEN\nEND IF\n", 1, "=="),
        ("WHILE TRUE DO\nOUTPUT 1\n", 1, "never closed"),
        ('output "hi"\n', 1, "capitals"),
        ("x = 1\nIF x > 0 then\nEND IF\n", 2, "THEN, not then"),
        ("totl = 1\nOUTPUT total\n", 2, "Did you mean totl?"),
        ("a = [1, 2]\nOUTPUT a[2]\n", 2, "positions 0 to 1"),
        (
            "FUNCTION f(n)\n  RETURN f(n + 1)\nEND FUNCTION\nOUTPUT f(1)\n",
            2,
            "stops calling itself",
        ),
        ("IF TRUE THEN\nEND WHILE\n", 2, "Expected END IF"),
        ("IF 5 THEN\nEND IF\n", 1, "TRUE or FALSE"),
        ("RETURN 1\n", 1, "inside a FUNCTION"),
        ("OUTPUT 1 / 0\n", 1, "divide by zero"),
        ('OUTPUT "abc\n', 1, "closing quote"),
        ("OUTPUT 1 < 2 < 3\n", 1, "one pair at a time"),
        ('OUTPUT TO_NUMBER("abc")\n', 1, "can't turn"),
        ("OUTPUT LENGTH(1, 2)\n", 1, "right number"),
        ("FUNCTION LENGTH(x)\nEND FUNCTION\n", 1, "built-in"),
    ],
)
def test_errors_explain_and_point_at_the_line(source, line, fragment, capsys):
    with pytest.raises(pseudo.PseudoError) as caught:
        pseudo.run_source(source)
    assert caught.value.line == line
    assert fragment in caught.value.message


def test_trace_records_lines_variables_and_frames():
    trace = pseudo.trace_source(
        'name = INPUT("Name? ")\nFUNCTION double(n)\n  RETURN n * 2\nEND FUNCTION\n'
        "x = double(4)\nOUTPUT name, x\n",
        ["Ada"],
    )
    assert trace["error"] is None
    assert [s["line"] for s in trace["steps"]] == [1, 5, 3, 6, 0]
    inside = trace["steps"][2]["frames"]
    assert [f["name"] for f in inside] == ["main program", "double"]
    assert inside[1]["vars"] == {"n": "4"}
    assert trace["steps"][3]["frames"][0]["vars"] == {"name": '"Ada"', "x": "8"}
    assert trace["output"] == "Name? Ada\nAda 8\n"
    assert trace["steps"][-1]["out"] == len(trace["output"])


def test_trace_error_keeps_variables_of_the_failing_function():
    trace = pseudo.trace_source(
        "FUNCTION f(items)\n  RETURN items[5]\nEND FUNCTION\nOUTPUT f([1])\n", []
    )
    assert trace["error"]["line"] == 2
    assert trace["steps"][-1]["frames"][1]["vars"] == {"items": "[1]"}


def test_trace_stops_endless_loops():
    trace = pseudo.trace_source("WHILE TRUE DO\n  x = 1\nEND WHILE\n", [])
    assert trace["truncated"] and len(trace["steps"]) == pseudo.MAX_TRACE_STEPS


def test_grader_runs_pseudocode_with_input_and_friendly_errors():
    result = grader.run_program(
        'n = TO_NUMBER(INPUT("N? "))\nOUTPUT n * 2\n', ["21"], language="pseudo"
    )
    assert result.stdout == "N? 42\n"
    failed = grader.run_program('OUTPUT "a" + 1\n', language="pseudo")
    explanation = explain_traceback(failed.stderr, 'OUTPUT "a" + 1\n')
    assert explanation.title == "Your program stopped"
    assert explanation.line == 1
    assert explanation.message.startswith("Can't add text and a number.")


def test_snippet_checks_see_pseudocode_variables():
    passed = grader.run_snippet("x = 2 + 2\n", "assert x == 4", language="pseudo")
    assert passed.passed
    failed = grader.run_snippet("x = \n", "assert x == 4", language="pseudo")
    assert not failed.passed and "nothing after the =" in failed.message


def test_trace_program_runs_the_script():
    trace = grader.trace_program("x = 1\nOUTPUT x\n", [])
    assert trace["output"] == "1\n" and trace["error"] is None


def test_command_line_trace(tmp_path):
    import subprocess

    program = tmp_path / "main.pseudo"
    program.write_text('OUTPUT INPUT("Q? ")\n', encoding="utf-8")
    script = Path(pseudo.__file__)
    proc = subprocess.run(
        [sys.executable, str(script), "--trace", str(program)],
        input="hi\n",
        capture_output=True,
        text=True,
    )
    assert json.loads(proc.stdout)["output"] == "Q? hi\nhi\n"
