import pytest

from dojo.explain import explain_message, explain_traceback

TRACEBACK = """Traceback (most recent call last):
  File "/work/run-abc/main.py", line 3, in <module>
    pirnt("hi")
    ^^^^^
NameError: name 'pirnt' is not defined. Did you mean: 'print'?
"""


def test_traceback_gives_line_and_suggestion():
    explanation = explain_traceback(TRACEBACK, code='x = 1\n\npirnt("hi")\n')
    assert explanation.title == "NameError"
    assert explanation.line == 3
    assert "Did you mean **`print`**?" in explanation.message
    assert explanation.raw.startswith("NameError: name 'pirnt'")


def test_no_exception_returns_none():
    assert explain_traceback("just some output") is None


def test_name_error_suggests_learner_variables():
    message = explain_message(
        "NameError: name 'totl' is not defined", code="total = 5\nprint(totl)"
    )
    assert "`total`" in message


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ("SyntaxError: expected ':'", "colon"),
        ("SyntaxError: '(' was never closed", "never closed"),
        ("IndentationError: expected an indented block after 'if' statement on line 1", "indented"),
        ('TypeError: can only concatenate str (not "int") to str', "str(...)"),
        ("ValueError: invalid literal for int() with base 10: 'abc'", "whole numbers"),
        ("AttributeError: 'list' object has no attribute 'push'", "A `list` doesn't have `.push`"),
        ("AttributeError: 'str' object has no attribute 'uper'", "`.upper`"),
        ("ZeroDivisionError: division by zero", "divided by zero"),
        ("IndexError: list index out of range", "start at 0"),
        ("ModuleNotFoundError: No module named 'pandas'", "Library Explorer"),
    ],
)
def test_common_errors(raw, fragment):
    assert fragment in explain_message(raw)


def test_unknown_errors_pass_through():
    assert explain_message("OSError: disk on fire") == "OSError: disk on fire"
    assert explain_message("Expected 3 lines but got 2") == "Expected 3 lines but got 2"


def test_source_locations_are_hidden():
    message = explain_message(
        "SyntaxError: invalid syntax (<ipython-input-4-f5b1313dc8c5>, line 1)"
    )
    assert "ipython-input" not in message and "line 1" not in message
    assert "main.py" not in explain_message("SyntaxError: bad thing (main.py, line 3)")
