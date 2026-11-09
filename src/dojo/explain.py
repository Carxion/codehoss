"""Friendly error explainer: Python tracebacks -> plain English for beginners.

Rule-based on purpose. It covers the errors beginners hit most; anything it doesn't
recognise falls back to the original message (the M8 tutor can do better there).
"""

from __future__ import annotations

import builtins
import difflib
import keyword
import re
from dataclasses import dataclass

EXCEPTION_LINE = re.compile(
    r"^(?P<type>[A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt)): ?(?P<msg>.*)$"
)
MAIN_LINE = re.compile(r'File "(?:.*/)?main\.py", line (?P<line>\d+)')
IDENTIFIER = re.compile(r"\b[A-Za-z_]\w*\b")
BUILTIN_NAMES = [n for n in dir(builtins) if not n.startswith("_")]


@dataclass
class Explanation:
    title: str
    message: str
    line: int | None
    raw: str


def explain_traceback(stderr: str, code: str = "") -> Explanation | None:
    """Explain the last exception in `stderr`, or None if there isn't one."""
    lines = [line for line in stderr.strip().splitlines() if line.strip()]
    exception = next((m for line in reversed(lines) if (m := EXCEPTION_LINE.match(line))), None)
    if exception is None:
        return None
    line_numbers = [int(m["line"]) for line in lines if (m := MAIN_LINE.search(line))]
    line = line_numbers[-1] if line_numbers else None
    title, message = explain(exception["type"], exception["msg"], code)
    return Explanation(title, message, line, exception.group(0))


def explain_message(raw: str, code: str = "") -> str:
    """Explain a one-line 'SomeError: message' string; returns it unchanged if unknown."""
    match = EXCEPTION_LINE.match(raw.strip())
    if match is None:
        return raw
    _, message = explain(match["type"], match["msg"], code)
    return message


def explain(error_type: str, msg: str, code: str = "") -> tuple[str, str]:
    error_type = error_type.rsplit(".", 1)[-1]
    handler = _HANDLERS.get(error_type)
    if handler:
        result = handler(msg, code)
        if result:
            return error_type, result
    return error_type, f"{error_type}: {msg}" if msg else error_type


# --- handlers -----------------------------------------------------------------


def _name_error(msg: str, code: str) -> str | None:
    match = re.search(r"name '(\w+)' is not defined", msg)
    if not match:
        return None
    name = match[1]
    known = set(BUILTIN_NAMES) | set(IDENTIFIER.findall(code)) - {name}
    suggestion = _closest(name, known)
    text = f"Python doesn't recognise `{name}`."
    if suggestion:
        return f"{text} Did you mean **`{suggestion}`**?"
    return (
        f"{text} If it's a variable, make sure you create it (with `=`) *before* this line. "
        "If it's text, put it in quotes."
    )


def _syntax_error(msg: str, code: str) -> str | None:
    lowered = msg.lower()
    if "expected ':'" in lowered:
        return (
            "A line that starts a block (`if`, `for`, `while`, `def`...) must end with a colon `:`."
        )
    if "was never closed" in lowered or "unexpected eof" in lowered:
        return 'A bracket or quote was opened but never closed. Check that every `(`, `[`, `{` and `"` has a partner.'
    if "unterminated string" in lowered:
        return (
            "A piece of text is missing its closing quote. Text must start *and* end with a quote."
        )
    if "perhaps you forgot a comma" in lowered:
        return "Python found two things next to each other. Did you forget a comma between them?"
    if "invalid syntax. maybe you meant '==' or ':='" in lowered or "cannot assign to" in lowered:
        return "To *compare* two values use `==` (two equals signs). A single `=` stores a value."
    if "invalid character" in lowered:
        return "There's a character Python can't read, often a curly quote (“ ”) pasted from a document. Retype the quotes."
    return f"Python couldn't understand this line ({msg}). Check spelling, brackets and colons."


def _indentation_error(msg: str, code: str) -> str | None:
    lowered = msg.lower()
    if "expected an indented block" in lowered:
        return "The line after a `:` must be indented (4 spaces) to show it belongs to that block."
    if "unexpected indent" in lowered:
        return "This line is indented but shouldn't be. Remove the spaces at the start."
    if "unindent does not match" in lowered:
        return (
            "This line's indentation doesn't line up with the lines above. Use 4 spaces per level."
        )
    return None


def _type_error(msg: str, code: str) -> str | None:
    if re.search(r'can only concatenate str \(not "(int|float)"\) to str', msg):
        return (
            "You're joining text and a number with `+`. Turn the number into text with "
            '`str(...)`, or use an f-string: `f"Total: {total}"`.'
        )
    if "unsupported operand type(s)" in msg and "'str'" in msg:
        return (
            "You're doing maths with text. Values from `input()` are text; "
            "convert them with `int(...)` or `float(...)` first."
        )
    if match := re.search(r"'(\w+)' object is not callable", msg):
        return f"You're using `()` on a {match[1]} as if it were a function. Did you reuse a function's name for a variable?"
    if match := re.search(r"missing (\d+) required positional argument", msg):
        return f"This function needs more values passed in: {match[1]} missing. Check the brackets of the call."
    return None


def _value_error(msg: str, code: str) -> str | None:
    if match := re.search(r"invalid literal for int\(\) with base 10: (.*)", msg):
        return (
            f"`int()` can only convert whole numbers, but it got {match[1]}. Check what was typed."
        )
    if "could not convert string to float" in msg:
        return "`float()` got text that isn't a number. Check what was typed."
    return None


def _attribute_error(msg: str, code: str) -> str | None:
    match = re.search(r"'(\w+)' object has no attribute '(\w+)'", msg)
    if not match:
        return None
    type_name, attr = match[1], match[2]
    builtin_type = getattr(builtins, type_name, None)
    options = [a for a in dir(builtin_type) if not a.startswith("_")] if builtin_type else []
    suggestion = _closest(attr, options)
    text = f"A `{type_name}` doesn't have `.{attr}`."
    return f"{text} Did you mean **`.{suggestion}`**?" if suggestion else text


def _simple(text: str):
    return lambda msg, code: text


_HANDLERS = {
    "NameError": _name_error,
    "SyntaxError": _syntax_error,
    "IndentationError": _indentation_error,
    "TabError": _simple("Mixing tabs and spaces confuses Python. Use 4 spaces for each level."),
    "TypeError": _type_error,
    "ValueError": _value_error,
    "AttributeError": _attribute_error,
    "ZeroDivisionError": _simple(
        "You divided by zero, which isn't allowed. Check the value you divide by."
    ),
    "IndexError": _simple(
        "You asked for a position that doesn't exist. Positions start at 0, "
        "so a list of 3 items has positions 0, 1 and 2."
    ),
    "KeyError": lambda msg, code: (
        f"The dictionary has no key {msg}. Check the spelling, or use `.get()`."
    ),
    "ModuleNotFoundError": lambda msg, code: (
        f"{msg[0].upper() + msg[1:] if msg else 'That module is not installed'}. "
        "It isn't installed for this course; the Library Explorer lists what is."
    ),
    "RecursionError": _simple(
        "A function kept calling itself without stopping. Check its stopping condition."
    ),
    "EOFError": _simple("The program asked for more input than was given."),
}


def _closest(name: str, options) -> str | None:
    options = [o for o in options if o != name and not keyword.iskeyword(o)]
    matches = difflib.get_close_matches(name, options, n=1, cutoff=0.75)
    return matches[0] if matches else None
