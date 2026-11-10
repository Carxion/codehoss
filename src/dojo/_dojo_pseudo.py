"""Dojo pseudocode: the small teaching language of the Programming Basics course.

Copied into sandbox runs as dojo_pseudo.py. Standard library only.

It reads like the pseudocode in textbooks and exam papers, and every idea in it maps
directly onto Python, JavaScript, R, C++ and C#:

    # comments start with # or //
    name = INPUT("What is your name? ")
    OUTPUT "Hello,", name
    IF age >= 18 THEN ... ELSE IF ... THEN ... ELSE ... END IF
    WHILE count < 5 DO ... END WHILE
    REPEAT ... UNTIL done
    FOR i FROM 1 TO 10 STEP 2 DO ... END FOR      (both ends included)
    FOR EACH item IN items DO ... END FOR
    FUNCTION area(width, height) ... RETURN width * height ... END FUNCTION

Values are numbers, text, TRUE/FALSE, lists [1, 2], maps {"key": value} and NOTHING.
It is deliberately strict (no mixing text and numbers, conditions must be TRUE or
FALSE) and its errors explain what went wrong in plain words.

    python dojo_pseudo.py main.pseudo           run it (INPUT reads the keyboard)
    python dojo_pseudo.py --trace main.pseudo   run it and print a JSON trace: each step's
                                                line, variables and output so far
    run_file(path) / run_source(code)           run it, get its variables back (pseudocode
                                                functions can be called from Python)
"""

from __future__ import annotations

import builtins
import difflib
import json
import random
import re
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

MAX_CALL_DEPTH = 200
MAX_TRACE_STEPS = 1000

KEYWORDS = {
    "IF", "THEN", "ELSE", "END", "WHILE", "DO", "FOR", "FROM", "TO", "STEP", "EACH", "IN",
    "REPEAT", "UNTIL", "FUNCTION", "RETURN", "OUTPUT", "AND", "OR", "NOT", "MOD", "DIV",
    "TRUE", "FALSE", "NOTHING",
}  # fmt: skip
# Keywords a line can start with: written in lower case they are almost always a slip.
STATEMENT_KEYWORDS = {"IF", "ELSE", "END", "WHILE", "FOR", "REPEAT", "UNTIL", "FUNCTION",
                      "RETURN", "OUTPUT"}  # fmt: skip
BLOCK_ENDS = {"IF", "WHILE", "FOR", "FUNCTION"}

TOKEN = re.compile(
    r"""
    (?P<space>[ \t\r]+)
  | (?P<comment>(?:\#|//)[^\n]*)
  | (?P<newline>\n)
  | (?P<number>\d+(?:\.\d+)?)
  | (?P<text>"[^"\n]*"|'[^'\n]*')
  | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>==|!=|<=|>=|[-+*/()\[\]{},:<>=])
    """,
    re.VERBOSE,
)


class PseudoError(Exception):
    """A mistake in the learner's program, explained for a beginner."""

    def __init__(self, message: str, line: int | None = None):
        self.message = message
        self.line = line
        self.frames: list | None = None  # variables when it happened (tracing only)
        super().__init__(f"Line {line}: {message}" if line else message)


# --- tokens ----------------------------------------------------------------------


@dataclass
class Token:
    kind: str  # number, text, word, keyword, op, newline, end
    value: Any
    line: int


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    line, pos = 1, 0
    while pos < len(source):
        match = TOKEN.match(source, pos)
        if match is None:
            char = source[pos]
            if char in "\"'":
                raise PseudoError("This text is missing its closing quote.", line)
            if char in "“”‘’":
                raise PseudoError(
                    f"{char} is a curly quote (often pasted from a document). "
                    'Type straight quotes instead: "like this".',
                    line,
                )
            raise PseudoError(f"The character {char!r} doesn't mean anything here.", line)
        kind, value = match.lastgroup, match.group()
        pos = match.end()
        if kind in ("space", "comment"):
            continue
        if kind == "newline":
            tokens.append(Token("newline", value, line))
            line += 1
        elif kind == "number":
            tokens.append(Token("number", float(value) if "." in value else int(value), line))
        elif kind == "text":
            tokens.append(Token("text", value[1:-1], line))
        elif kind == "word":
            tokens.append(Token("keyword" if value in KEYWORDS else "word", value, line))
        else:
            tokens.append(Token("op", value, line))
    tokens.append(Token("newline", "\n", line))
    tokens.append(Token("end", None, line))
    return tokens


# --- syntax tree -----------------------------------------------------------------


@dataclass
class Node:
    line: int


@dataclass
class Literal(Node):
    value: Any


@dataclass
class Name(Node):
    name: str


@dataclass
class ListLit(Node):
    items: list


@dataclass
class MapLit(Node):
    pairs: list


@dataclass
class Index(Node):
    target: Node
    index: Node


@dataclass
class Call(Node):
    name: str
    args: list


@dataclass
class Unary(Node):
    op: str
    operand: Node


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Assign(Node):
    target: Node
    value: Node


@dataclass
class Output(Node):
    values: list


@dataclass
class If(Node):
    branches: list  # [(line, condition, body)]
    otherwise: list | None


@dataclass
class While(Node):
    condition: Node
    body: list


@dataclass
class Repeat(Node):
    body: list
    condition: Node
    until_line: int


@dataclass
class For(Node):
    var: str
    start: Node
    stop: Node
    step: Node | None
    body: list


@dataclass
class ForEach(Node):
    var: str
    items: Node
    body: list


@dataclass
class FunctionDef(Node):
    name: str
    params: list
    body: list


@dataclass
class Return(Node):
    value: Node | None


@dataclass
class ExprStatement(Node):
    expr: Node


# --- parser ----------------------------------------------------------------------


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.in_function = False

    # helpers
    @property
    def tok(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def advance(self) -> Token:
        tok = self.tok
        self.pos += 1
        return tok

    def at(self, kind: str, value: Any = None) -> bool:
        return self.tok.kind == kind and (value is None or self.tok.value == value)

    def at_keyword(self, *words: str) -> bool:
        return self.tok.kind == "keyword" and self.tok.value in words

    def expect_keyword(self, word: str, message: str) -> Token:
        if self.tok.kind == "word" and self.tok.value.upper() == word:
            raise PseudoError(f"Keywords are written in capitals: write {word}, not "
                              f"{self.tok.value}.", self.tok.line)  # fmt: skip
        if not self.at_keyword(word):
            raise PseudoError(message, self.tok.line)
        return self.advance()

    def expect_op(self, op: str, message: str) -> Token:
        if not self.at("op", op):
            raise PseudoError(message, self.tok.line)
        return self.advance()

    def skip_newlines(self) -> None:
        while self.at("newline"):
            self.advance()

    def end_of_statement(self) -> None:
        if self.at("op", "="):
            raise PseudoError(
                "To compare two values use == (two equals signs). One = stores a value.",
                self.tok.line,
            )
        if not self.at("newline"):
            raise PseudoError(
                f"Didn't expect {describe(self.tok)} here. Each instruction goes on its own line.",
                self.tok.line,
            )
        self.advance()

    # statements
    def parse_program(self) -> list:
        body = self.parse_block()
        if not self.at("end"):
            tok = self.tok
            what = f"END {self.peek().value}" if tok.value == "END" else tok.value
            raise PseudoError(f"This {what} has no matching start above it.", tok.line)
        return body

    def parse_block(self) -> list:
        body = []
        self.skip_newlines()
        while not self.at("end") and not self.at_keyword("END", "ELSE", "UNTIL"):
            body.append(self.parse_statement())
            self.skip_newlines()
        return body

    def close_block(self, opener: str, line: int) -> None:
        if self.at("end"):
            raise PseudoError(
                f"The {opener} on line {line} is never closed. Add END {opener} after "
                "its last instruction.",
                line,
            )
        if not self.at_keyword("END"):
            word = self.tok.value
            raise PseudoError(
                f"{word} doesn't belong to the {opener} on line {line}. "
                f"Close the {opener} with END {opener}.",
                self.tok.line,
            )
        end = self.advance()
        closes = self.tok.value if self.tok.kind == "keyword" else None
        if closes != opener:
            what = f"END {closes}" if closes else "END"
            raise PseudoError(
                f"Expected END {opener} to close the {opener} on line {line}, but found {what}.",
                end.line,
            )
        self.advance()
        self.end_of_statement()

    def parse_statement(self) -> Node:
        tok = self.tok
        if tok.kind == "word" and tok.value.upper() in STATEMENT_KEYWORDS:
            nxt = self.peek()
            if not (nxt.kind == "op" and nxt.value in ("=", "[", "(")):
                raise PseudoError(
                    f"Keywords are written in capitals: write {tok.value.upper()}, "
                    f"not {tok.value}.",
                    tok.line,
                )
        if tok.kind == "keyword":
            handler = {
                "OUTPUT": self.parse_output,
                "IF": self.parse_if,
                "WHILE": self.parse_while,
                "REPEAT": self.parse_repeat,
                "FOR": self.parse_for,
                "FUNCTION": self.parse_function,
                "RETURN": self.parse_return,
            }.get(tok.value)
            if handler is None:
                raise PseudoError(f"A line can't start with {tok.value}.", tok.line)
            return handler()

        expr = self.parse_expression()
        if self.at("op", "="):
            if not isinstance(expr, Name | Index):
                raise PseudoError(
                    "The left side of = must be a variable name (or a list position like "
                    "scores[0]).",
                    tok.line,
                )
            self.advance()
            if self.at("newline"):
                raise PseudoError("There's nothing after the = to store.", tok.line)
            value = self.parse_expression()
            self.end_of_statement()
            return Assign(tok.line, expr, value)
        if isinstance(expr, Name):
            raise PseudoError(
                f"{expr.name} on its own does nothing. To store a value write "
                f"{expr.name} = ..., to show it write OUTPUT {expr.name}.",
                tok.line,
            )
        if not isinstance(expr, Call):
            raise PseudoError(
                "This line works out a value but doesn't do anything with it. "
                "Store it (x = ...) or show it (OUTPUT ...).",
                tok.line,
            )
        self.end_of_statement()
        return ExprStatement(tok.line, expr)

    def parse_output(self) -> Node:
        line = self.advance().line
        if self.at("newline"):
            raise PseudoError('OUTPUT needs something to show, e.g. OUTPUT "Hello".', line)
        values = [self.parse_expression()]
        while self.at("op", ","):
            self.advance()
            values.append(self.parse_expression())
        self.end_of_statement()
        return Output(line, values)

    def parse_condition(self, keyword: str, then: str) -> Node:
        if self.at("newline") or self.at_keyword(then):
            raise PseudoError(f"{keyword} needs a condition, e.g. {keyword} x > 5 {then}.",
                              self.tok.line)  # fmt: skip
        condition = self.parse_expression()
        if self.at("op", "="):
            raise PseudoError(
                "To compare two values use == (two equals signs). One = stores a value.",
                self.tok.line,
            )
        return condition

    def parse_if(self) -> Node:
        line = self.advance().line
        condition = self.parse_condition("IF", "THEN")
        self.expect_keyword("THEN", "IF needs THEN at the end of its line: IF ... THEN")
        self.end_of_statement()
        branches = [(line, condition, self.parse_block())]
        otherwise = None
        while self.at_keyword("ELSE"):
            else_line = self.advance().line
            if self.at_keyword("IF"):
                self.advance()
                condition = self.parse_condition("ELSE IF", "THEN")
                self.expect_keyword(
                    "THEN", "ELSE IF needs THEN at the end of its line: ELSE IF ... THEN"
                )
                self.end_of_statement()
                branches.append((else_line, condition, self.parse_block()))
            else:
                self.end_of_statement()
                otherwise = self.parse_block()
                if self.at_keyword("ELSE"):
                    raise PseudoError(
                        "ELSE must be the last part of an IF. Move this ELSE IF above it.",
                        self.tok.line,
                    )
        if self.at_keyword("UNTIL"):
            raise PseudoError(f"UNTIL doesn't belong to the IF on line {line}.", self.tok.line)
        self.close_block("IF", line)
        return If(line, branches, otherwise)

    def parse_while(self) -> Node:
        line = self.advance().line
        condition = self.parse_condition("WHILE", "DO")
        self.expect_keyword("DO", "WHILE needs DO at the end of its line: WHILE ... DO")
        self.end_of_statement()
        body = self.parse_block()
        self.check_no_stray("WHILE", line)
        self.close_block("WHILE", line)
        return While(line, condition, body)

    def parse_repeat(self) -> Node:
        line = self.advance().line
        self.end_of_statement()
        body = self.parse_block()
        if not self.at_keyword("UNTIL"):
            if self.at("end"):
                raise PseudoError(
                    f"The REPEAT on line {line} needs UNTIL <condition> after its last "
                    "instruction.",
                    line,
                )
            raise PseudoError(f"Expected UNTIL to finish the REPEAT on line {line}.", self.tok.line)
        until_line = self.advance().line
        condition = self.parse_condition("UNTIL", "")
        self.end_of_statement()
        return Repeat(line, body, condition, until_line)

    def parse_for(self) -> Node:
        line = self.advance().line
        if self.at_keyword("EACH"):
            self.advance()
            var = self.expect_name("FOR EACH needs a variable name: FOR EACH item IN items DO")
            self.expect_keyword("IN", "Write FOR EACH item IN items DO")
            items = self.parse_expression()
            self.expect_keyword("DO", "FOR EACH needs DO at the end of its line")
            self.end_of_statement()
            body = self.parse_block()
            self.check_no_stray("FOR", line)
            self.close_block("FOR", line)
            return ForEach(line, var, items, body)
        var = self.expect_name("FOR needs a variable name: FOR i FROM 1 TO 10 DO")
        if self.at_keyword("IN"):
            raise PseudoError("To go through a list write FOR EACH item IN items DO.", line)
        self.expect_keyword("FROM", "Write FOR i FROM 1 TO 10 DO")
        start = self.parse_expression()
        self.expect_keyword("TO", "Write FOR i FROM 1 TO 10 DO (TO is missing)")
        stop = self.parse_expression()
        step = None
        if self.at_keyword("STEP"):
            self.advance()
            step = self.parse_expression()
        self.expect_keyword("DO", "FOR needs DO at the end of its line: FOR i FROM 1 TO 10 DO")
        self.end_of_statement()
        body = self.parse_block()
        self.check_no_stray("FOR", line)
        self.close_block("FOR", line)
        return For(line, var, start, stop, step, body)

    def check_no_stray(self, opener: str, line: int) -> None:
        if self.at_keyword("ELSE", "UNTIL"):
            raise PseudoError(
                f"{self.tok.value} doesn't belong to the {opener} on line {line}.",
                self.tok.line,
            )

    def parse_function(self) -> Node:
        line = self.advance().line
        if self.in_function:
            raise PseudoError("A FUNCTION can't be written inside another FUNCTION.", line)
        name = self.expect_name("FUNCTION needs a name: FUNCTION greet(name)")
        self.expect_op("(", f"Put brackets after the name, even if empty: FUNCTION {name}()")
        params: list[str] = []
        while not self.at("op", ")"):
            param = self.expect_name("The brackets hold the names of the values it takes.")
            if param in params:
                raise PseudoError(f"{param} is listed twice.", line)
            params.append(param)
            if not self.at("op", ")"):
                self.expect_op(",", "Separate the names in the brackets with commas.")
        self.advance()
        self.end_of_statement()
        self.in_function = True
        try:
            body = self.parse_block()
        finally:
            self.in_function = False
        self.check_no_stray("FUNCTION", line)
        self.close_block("FUNCTION", line)
        return FunctionDef(line, name, params, body)

    def parse_return(self) -> Node:
        line = self.advance().line
        if not self.in_function:
            raise PseudoError("RETURN can only be used inside a FUNCTION.", line)
        value = None if self.at("newline") else self.parse_expression()
        self.end_of_statement()
        return Return(line, value)

    def expect_name(self, message: str) -> str:
        if self.tok.kind != "word":
            raise PseudoError(message, self.tok.line)
        return self.advance().value

    # expressions, lowest precedence first
    def parse_expression(self) -> Node:
        return self.parse_or()

    def parse_or(self) -> Node:
        left = self.parse_and()
        while self.at_keyword("OR"):
            line = self.advance().line
            left = Binary(line, "OR", left, self.parse_and())
        return left

    def parse_and(self) -> Node:
        left = self.parse_not()
        while self.at_keyword("AND"):
            line = self.advance().line
            left = Binary(line, "AND", left, self.parse_not())
        return left

    def parse_not(self) -> Node:
        if self.at_keyword("NOT"):
            line = self.advance().line
            return Unary(line, "NOT", self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self) -> Node:
        left = self.parse_sum()
        if self.at("op") and self.tok.value in ("==", "!=", "<", ">", "<=", ">="):
            op = self.advance()
            left = Binary(op.line, op.value, left, self.parse_sum())
            if self.at("op") and self.tok.value in ("==", "!=", "<", ">", "<=", ">="):
                raise PseudoError(
                    "Compare one pair at a time and join them with AND, e.g. 1 <= x AND x <= 10.",
                    op.line,
                )
        return left

    def parse_sum(self) -> Node:
        left = self.parse_product()
        while self.at("op") and self.tok.value in ("+", "-"):
            op = self.advance()
            left = Binary(op.line, op.value, left, self.parse_product())
        return left

    def parse_product(self) -> Node:
        left = self.parse_unary()
        while (self.at("op") and self.tok.value in ("*", "/")) or self.at_keyword("MOD", "DIV"):
            op = self.advance()
            left = Binary(op.line, op.value, left, self.parse_unary())
        return left

    def parse_unary(self) -> Node:
        if self.at("op", "-"):
            line = self.advance().line
            return Unary(line, "-", self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self) -> Node:
        expr = self.parse_atom()
        while self.at("op", "["):
            line = self.advance().line
            index = self.parse_expression()
            self.expect_op("]", "A [ was opened but not closed with ].")
            expr = Index(line, expr, index)
        return expr

    def parse_atom(self) -> Node:
        tok = self.tok
        if tok.kind in ("number", "text"):
            self.advance()
            return Literal(tok.line, tok.value)
        if tok.kind == "keyword" and tok.value in ("TRUE", "FALSE", "NOTHING"):
            self.advance()
            return Literal(tok.line, {"TRUE": True, "FALSE": False, "NOTHING": None}[tok.value])
        if tok.kind == "word":
            self.advance()
            if self.at("op", "("):
                self.advance()
                args = []
                while not self.at("op", ")"):
                    if self.at("newline"):
                        raise PseudoError(
                            f"The ( after {tok.value} is never closed with ).", tok.line
                        )
                    args.append(self.parse_expression())
                    if not self.at("op", ")"):
                        self.expect_op(",", "Separate the values in brackets with commas.")
                self.advance()
                return Call(tok.line, tok.value, args)
            return Name(tok.line, tok.value)
        if tok.kind == "op" and tok.value == "(":
            self.advance()
            expr = self.parse_expression()
            self.expect_op(")", "A ( was opened but not closed with ).")
            return expr
        if tok.kind == "op" and tok.value == "[":
            self.advance()
            items = []
            while not self.at("op", "]"):
                if self.at("newline"):
                    raise PseudoError("A list's [ must be closed with ] on the same line.",
                                      tok.line)  # fmt: skip
                items.append(self.parse_expression())
                if not self.at("op", "]"):
                    self.expect_op(",", "Separate the items in a list with commas.")
            self.advance()
            return ListLit(tok.line, items)
        if tok.kind == "op" and tok.value == "{":
            self.advance()
            pairs = []
            while not self.at("op", "}"):
                if self.at("newline"):
                    raise PseudoError("A map's { must be closed with } on the same line.",
                                      tok.line)  # fmt: skip
                key = self.parse_expression()
                self.expect_op(":", 'Write each entry as key: value, e.g. {"name": "Ada"}.')
                pairs.append((key, self.parse_expression()))
                if not self.at("op", "}"):
                    self.expect_op(",", "Separate the entries in a map with commas.")
            self.advance()
            return MapLit(tok.line, pairs)
        if tok.kind == "newline":
            raise PseudoError("This line ends too early: a value is missing.", tok.line)
        if tok.kind == "word" or tok.kind == "keyword":
            raise PseudoError(f"Didn't expect {tok.value} here.", tok.line)
        raise PseudoError(f"Didn't expect {describe(tok)} here.", tok.line)


def describe(tok: Token) -> str:
    if tok.kind == "newline":
        return "the end of the line"
    if tok.kind == "text":
        return f'"{tok.value}"'
    return str(tok.value)


def parse(source: str) -> list:
    return Parser(tokenize(source)).parse_program()


# --- values ----------------------------------------------------------------------


def is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def kind_of(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE/FALSE"
    if is_number(value):
        return "a number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "a map"
    if isinstance(value, Function):
        return "a function"
    return "NOTHING"


def show(value: Any, nested: bool = False) -> str:
    """How a value looks when shown. Inside lists and maps, text keeps its quotes."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return "NOTHING"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, str):
        return f'"{value}"' if nested else value
    if isinstance(value, list):
        return "[" + ", ".join(show(v, True) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{show(k, True)}: {show(v, True)}" for k, v in value.items()) + "}"
    if isinstance(value, Function):
        return f"FUNCTION {value.name}({', '.join(value.params)})"
    return str(value)


def tidy(number: float) -> int | float:
    """Whole-number results stay whole: 6 / 2 is 3, not 3.0."""
    if isinstance(number, float) and number.is_integer() and abs(number) < 2**53:
        return int(number)
    return number


@dataclass
class Function:
    name: str
    params: list
    body: list
    line: int
    interpreter: Interpreter = field(repr=False, compare=False)

    def __call__(self, *args: Any) -> Any:
        """Lets tests call a learner's pseudocode function from Python."""
        return self.interpreter.call(self, list(args), self.line)


class ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


class TraceFull(Exception):
    pass


# --- interpreter -----------------------------------------------------------------


@dataclass
class Frame:
    name: str
    vars: dict


class Interpreter:
    def __init__(self, trace: bool = False, inputs: list[str] | None = None):
        self.globals: dict[str, Any] = {}
        self.frames = [Frame("main program", self.globals)]
        self.trace = trace
        self.steps: list[dict] = []
        self.output: list[str] = []  # only collected when tracing
        self.inputs = list(inputs or [])
        self.builtins = {
            "INPUT": self.b_input,
            "LENGTH": b_length,
            "APPEND": b_append,
            "REMOVE": b_remove,
            "TO_NUMBER": b_to_number,
            "TO_TEXT": lambda value: show(value),
            "ROUND": b_round,
            "RANDOM": b_random,
            "UPPER": lambda text: text_arg("UPPER", text).upper(),
            "LOWER": lambda text: text_arg("LOWER", text).lower(),
            "CONTAINS": b_contains,
            "KEYS": b_keys,
        }

    # running
    def run(self, program: list) -> dict[str, Any]:
        for statement in program:
            if isinstance(statement, FunctionDef):  # functions can be used before they're written
                if statement.name in self.builtins:
                    raise PseudoError(f"{statement.name} is already a built-in function; "
                                      "pick another name.", statement.line)  # fmt: skip
                self.globals[statement.name] = Function(
                    statement.name, statement.params, statement.body, statement.line, self
                )
        self.exec_block(program)
        return self.globals

    def write(self, text: str) -> None:
        if self.trace:
            self.output.append(text + "\n")
        else:
            print(text)

    def step(self, line: int) -> None:
        if not self.trace:
            return
        if len(self.steps) >= MAX_TRACE_STEPS:
            raise TraceFull()
        self.steps.append({"line": line, "frames": self.snapshot(), "out": self.output_length})

    @property
    def output_length(self) -> int:
        return sum(len(text) for text in self.output)

    def snapshot(self) -> list[dict]:
        return [
            {"name": f.name, "vars": {k: show(v, True) for k, v in f.vars.items()
                                      if not isinstance(v, Function)}}
            for f in self.frames
        ]  # fmt: skip

    @property
    def scope(self) -> dict:
        return self.frames[-1].vars

    def exec_block(self, body: list) -> None:
        for statement in body:
            self.exec(statement)

    def exec(self, s: Node) -> None:
        if isinstance(s, FunctionDef):
            return
        self.step(s.line)
        if isinstance(s, Assign):
            value = self.eval(s.value)
            if isinstance(value, Function) and isinstance(s.value, Name):
                raise PseudoError(
                    f"{s.value.name} is a function. To use it, call it with brackets: "
                    f"{s.value.name}(...)",
                    s.line,
                )
            self.assign(s.target, value, s.line)
        elif isinstance(s, Output):
            self.write(" ".join(show(self.eval(v)) for v in s.values))
        elif isinstance(s, If):
            for i, (line, condition, body) in enumerate(s.branches):
                if i:
                    self.step(line)
                if self.truth(condition, "ELSE IF" if i else "IF"):
                    self.exec_block(body)
                    return
            if s.otherwise is not None:
                self.exec_block(s.otherwise)
        elif isinstance(s, While):
            first = True
            while True:
                if not first:
                    self.step(s.line)
                first = False
                if not self.truth(s.condition, "WHILE"):
                    break
                self.exec_block(s.body)
        elif isinstance(s, Repeat):
            while True:
                self.exec_block(s.body)
                self.step(s.until_line)
                if self.truth(s.condition, "UNTIL"):
                    break
        elif isinstance(s, For):
            self.exec_for(s)
        elif isinstance(s, ForEach):
            items = self.eval(s.items)
            if isinstance(items, dict):
                items = list(items)
            elif isinstance(items, str):
                items = list(items)
            elif isinstance(items, list):
                items = list(items)  # a copy: adding to the list inside the loop is safe
            else:
                raise PseudoError(
                    f"FOR EACH goes through a list, text or map, but this is {kind_of(items)}.",
                    s.line,
                )
            for n, item in enumerate(items):
                if n:
                    self.step(s.line)
                self.scope[s.var] = item
                self.exec_block(s.body)
        elif isinstance(s, Return):
            raise ReturnSignal(None if s.value is None else self.eval(s.value))
        elif isinstance(s, ExprStatement):
            self.eval(s.expr)

    def exec_for(self, s: For) -> None:
        start, stop = self.eval(s.start), self.eval(s.stop)
        step = 1 if s.step is None else self.eval(s.step)
        for label, value in (("FROM", start), ("TO", stop), ("STEP", step)):
            if not is_number(value):
                raise PseudoError(f"FOR ... {label} needs a number, but got {kind_of(value)}.",
                                  s.line)  # fmt: skip
        if step == 0:
            raise PseudoError("STEP 0 would repeat forever. Use a positive or negative STEP.",
                              s.line)  # fmt: skip
        value = start
        first = True
        while (step > 0 and value <= stop) or (step < 0 and value >= stop):
            if not first:
                self.step(s.line)
            first = False
            self.scope[s.var] = value
            self.exec_block(s.body)
            value = tidy(value + step)

    def assign(self, target: Node, value: Any, line: int) -> None:
        if isinstance(target, Name):
            if target.name in self.builtins:
                raise PseudoError(f"{target.name} is a built-in function; pick another name.",
                                  line)  # fmt: skip
            self.scope[target.name] = value
            return
        assert isinstance(target, Index)
        container = self.eval(target.target)
        key = self.eval(target.index)
        if isinstance(container, list):
            position = self.position(container, key, line)
            container[position] = value
        elif isinstance(container, dict):
            container[hashable(key, line)] = value
        elif isinstance(container, str):
            raise PseudoError(
                "Text can't be changed one letter at a time. Build new text instead.", line
            )
        else:
            raise PseudoError(f"Only lists and maps have positions; this is {kind_of(container)}.",
                              line)  # fmt: skip

    def truth(self, condition: Node, where: str) -> bool:
        value = self.eval(condition)
        if not isinstance(value, bool):
            raise PseudoError(
                f"{where} needs a condition that is TRUE or FALSE, like score > 50, "
                f"but this one gives {kind_of(value)} ({show(value, True)}).",
                condition.line,
            )
        return value

    def position(self, items: list | str, key: Any, line: int) -> int:
        if not is_number(key) or not float(key).is_integer():
            raise PseudoError(f"Positions are whole numbers, but got {show(key, True)}.", line)
        key = int(key)
        if not 0 <= key < len(items):
            what = "letters" if isinstance(items, str) else "items"
            if not items:
                raise PseudoError(f"There is no position {key}: it has no {what}.", line)
            raise PseudoError(
                f"There is no position {key}. It has {len(items)} {what}, at positions "
                f"0 to {len(items) - 1} (positions start at 0).",
                line,
            )
        return key

    # expressions
    def eval(self, e: Node) -> Any:
        if isinstance(e, Literal):
            return e.value
        if isinstance(e, Name):
            return self.lookup(e)
        if isinstance(e, ListLit):
            return [self.eval(item) for item in e.items]
        if isinstance(e, MapLit):
            return {hashable(self.eval(k), e.line): self.eval(v) for k, v in e.pairs}
        if isinstance(e, Index):
            container = self.eval(e.target)
            key = self.eval(e.index)
            if isinstance(container, list | str):
                return container[self.position(container, key, e.line)]
            if isinstance(container, dict):
                key = hashable(key, e.line)
                if key not in container:
                    keys = ", ".join(show(k, True) for k in container) or "none"
                    raise PseudoError(f"The map has no key {show(key, True)}. Its keys: {keys}.",
                                      e.line)  # fmt: skip
                return container[key]
            raise PseudoError(f"Only lists, text and maps have positions; this is "
                              f"{kind_of(container)}.", e.line)  # fmt: skip
        if isinstance(e, Call):
            return self.eval_call(e)
        if isinstance(e, Unary):
            value = self.eval(e.operand)
            if e.op == "NOT":
                if not isinstance(value, bool):
                    raise PseudoError(f"NOT works on TRUE/FALSE, but got {kind_of(value)}.",
                                      e.line)  # fmt: skip
                return not value
            if not is_number(value):
                raise PseudoError(f"Only numbers can be negative; this is {kind_of(value)}.",
                                  e.line)  # fmt: skip
            return -value
        if isinstance(e, Binary):
            return self.eval_binary(e)
        raise AssertionError(e)

    def lookup(self, e: Name) -> Any:
        for scope in (self.scope, self.globals):
            if e.name in scope:
                return scope[e.name]
        if e.name in self.builtins:
            raise PseudoError(f"{e.name} is a function: call it with brackets, {e.name}(...).",
                              e.line)  # fmt: skip
        if e.name.upper() in KEYWORDS:
            raise PseudoError(f"Keywords are written in capitals: {e.name.upper()}.", e.line)
        known = [*self.scope, *self.globals, *self.builtins]
        close = difflib.get_close_matches(e.name, known, n=1, cutoff=0.75)
        if close:
            raise PseudoError(f"{e.name} has no value. Did you mean {close[0]}?", e.line)
        raise PseudoError(
            f"{e.name} has no value yet. Give it one first (e.g. {e.name} = 0), or if it's "
            f'meant to be text, put it in quotes: "{e.name}".',
            e.line,
        )

    def eval_call(self, e: Call) -> Any:
        args = [self.eval(a) for a in e.args]
        if e.name in self.builtins:
            try:
                return self.builtins[e.name](*args)
            except PseudoError as err:
                err.line = err.line or e.line
                raise PseudoError(err.message, err.line) from None
            except TypeError:
                raise PseudoError(
                    f"{e.name} was given {len(args)} value(s), which isn't the right number. "
                    f"{BUILTIN_USAGE.get(e.name, '')}",
                    e.line,
                ) from None
        target = self.scope.get(e.name, self.globals.get(e.name))
        if isinstance(target, Function):
            return self.call(target, args, e.line)
        if target is not None or e.name in self.scope or e.name in self.globals:
            raise PseudoError(f"{e.name} is {kind_of(target)}, not a function.", e.line)
        if e.name.upper() in self.builtins:
            raise PseudoError(f"Built-in functions are written in capitals: {e.name.upper()}.",
                              e.line)  # fmt: skip
        known = [n for n, v in self.globals.items() if isinstance(v, Function)]
        close = difflib.get_close_matches(e.name, [*known, *self.builtins], n=1, cutoff=0.7)
        hint = f" Did you mean {close[0]}?" if close else ""
        raise PseudoError(f"There's no function called {e.name}.{hint}", e.line)

    def call(self, function: Function, args: list, line: int) -> Any:
        if len(args) != len(function.params):
            wanted = ", ".join(function.params) or "nothing"
            raise PseudoError(
                f"{function.name} takes {len(function.params)} value(s) ({wanted}), but was "
                f"given {len(args)}.",
                line,
            )
        if len(self.frames) > MAX_CALL_DEPTH:
            raise PseudoError(
                f"More than {MAX_CALL_DEPTH} function calls inside each other. Does "
                f"{function.name} always reach a point where it stops calling itself?",
                line,
            )
        self.frames.append(Frame(function.name, dict(zip(function.params, args, strict=True))))
        try:
            self.exec_block(function.body)
            return None
        except ReturnSignal as signal:
            return signal.value
        except PseudoError as err:
            if self.trace and err.frames is None:
                err.frames = self.snapshot()  # before this function's variables are gone
            raise
        finally:
            self.frames.pop()

    def eval_binary(self, e: Binary) -> Any:
        op = e.op
        if op in ("AND", "OR"):
            left = self.eval(e.left)
            if not isinstance(left, bool):
                raise PseudoError(f"{op} joins TRUE/FALSE values, but the left side is "
                                  f"{kind_of(left)}.", e.line)  # fmt: skip
            if (op == "AND" and not left) or (op == "OR" and left):
                return left
            right = self.eval(e.right)
            if not isinstance(right, bool):
                raise PseudoError(f"{op} joins TRUE/FALSE values, but the right side is "
                                  f"{kind_of(right)}.", e.line)  # fmt: skip
            return right
        left, right = self.eval(e.left), self.eval(e.right)
        if op == "==":
            return same(left, right)
        if op == "!=":
            return not same(left, right)
        if op in ("<", ">", "<=", ">="):
            if not ((is_number(left) and is_number(right)) or
                    (isinstance(left, str) and isinstance(right, str))):  # fmt: skip
                raise PseudoError(
                    f"Can't compare {kind_of(left)} with {kind_of(right)} using {op}."
                    + (" Values from INPUT are text: use TO_NUMBER(...) first."
                       if str in (type(left), type(right)) else ""),
                    e.line,
                )  # fmt: skip
            return {"<": left < right, ">": left > right, "<=": left <= right,
                    ">=": left >= right}[op]  # fmt: skip
        if op == "+":
            if is_number(left) and is_number(right):
                return tidy(left + right)
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            hint = ""
            if {type(left), type(right)} & {str} and (is_number(left) or is_number(right)):
                hint = (
                    " To join a number onto text, make it text first: TO_TEXT(number)."
                    " To do maths with text that holds a number, use TO_NUMBER(text)."
                )
            raise PseudoError(f"Can't add {kind_of(left)} and {kind_of(right)}.{hint}", e.line)
        if not (is_number(left) and is_number(right)):
            name = {"-": "subtract", "*": "multiply", "/": "divide", "MOD": "use MOD on",
                    "DIV": "use DIV on"}[op]  # fmt: skip
            hint = (
                " Values from INPUT are text: use TO_NUMBER(...) first."
                if str in (type(left), type(right))
                else ""
            )
            raise PseudoError(f"Can only {name} numbers, not {kind_of(left)} and "
                              f"{kind_of(right)}.{hint}", e.line)  # fmt: skip
        if op in ("/", "MOD", "DIV") and right == 0:
            raise PseudoError("Can't divide by zero.", e.line)
        if op == "-":
            return tidy(left - right)
        if op == "*":
            return tidy(left * right)
        if op == "/":
            return tidy(left / right)
        if op == "MOD":
            return tidy(left % right)
        return tidy(left // right)

    # INPUT needs the interpreter: when tracing, typed answers come from a list
    def b_input(self, prompt: Any = "") -> str:
        prompt = show(prompt)
        if not self.trace:
            return builtins.input(prompt)
        if not self.inputs:
            raise PseudoError(
                "INPUT asked for a value, but no more input was given. Add a line to the "
                "input box for each INPUT.",
            )
        value = self.inputs.pop(0)
        self.output.append(f"{prompt}{value}\n")  # echoed, like a terminal
        return value


# --- built-in functions ------------------------------------------------------------

BUILTIN_USAGE = {
    "INPUT": 'INPUT("question") gives back what was typed, as text.',
    "LENGTH": "LENGTH(list or text) counts the items or letters.",
    "APPEND": "APPEND(list, item) adds item to the end of list.",
    "REMOVE": "REMOVE(list, position) takes out the item at that position.",
    "TO_NUMBER": 'TO_NUMBER("42") turns text into a number.',
    "TO_TEXT": "TO_TEXT(42) turns a value into text.",
    "ROUND": "ROUND(number) or ROUND(number, decimal places).",
    "RANDOM": "RANDOM(low, high) picks a whole number from low to high.",
    "UPPER": "UPPER(text) gives back the text in capitals.",
    "LOWER": "LOWER(text) gives back the text in small letters.",
    "CONTAINS": "CONTAINS(list, text or map, value) is TRUE if the value is in it.",
    "KEYS": "KEYS(map) gives back a list of the map's keys.",
}


def text_arg(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise PseudoError(f"{name} works on text, but got {kind_of(value)}.")
    return value


def b_length(value: Any) -> int:
    if not isinstance(value, list | str | dict):
        raise PseudoError(f"LENGTH counts a list, text or map, but got {kind_of(value)}.")
    return len(value)


def b_append(items: Any, item: Any) -> None:
    if not isinstance(items, list):
        raise PseudoError(f"APPEND adds to a list, but got {kind_of(items)}.")
    items.append(item)


def b_remove(items: Any, position: Any) -> Any:
    if not isinstance(items, list):
        raise PseudoError(f"REMOVE takes from a list, but got {kind_of(items)}.")
    if not is_number(position) or not 0 <= position < len(items) or position != int(position):
        raise PseudoError(
            f"REMOVE needs a position from 0 to {len(items) - 1}, but got {show(position, True)}."
        )
    return items.pop(int(position))


def b_to_number(value: Any) -> int | float:
    if is_number(value):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        if re.fullmatch(r"-?(\d+\.\d*|\.\d+)", text):
            return tidy(float(text))
    raise PseudoError(f"TO_NUMBER can't turn {show(value, True)} into a number.")


def b_round(value: Any, places: Any = 0) -> int | float:
    if not is_number(value) or not is_number(places):
        raise PseudoError("ROUND works on numbers: ROUND(3.14159, 2) gives 3.14.")
    exponent = Decimal(1).scaleb(-int(places))
    rounded = float(Decimal(str(value)).quantize(exponent, rounding=ROUND_HALF_UP))
    return tidy(rounded)


def b_random(low: Any, high: Any) -> int:
    if not (is_number(low) and is_number(high)) or low > high:
        raise PseudoError("RANDOM(low, high) needs two numbers, the first not bigger.")
    return random.randint(int(low), int(high))


def b_contains(collection: Any, item: Any) -> bool:
    if isinstance(collection, str):
        return isinstance(item, str) and item in collection
    if isinstance(collection, list):
        return any(same(item, x) for x in collection)
    if isinstance(collection, dict):
        return isinstance(item, str | int | float) and item in collection
    raise PseudoError(f"CONTAINS looks inside a list, text or map, not {kind_of(collection)}.")


def b_keys(value: Any) -> list:
    if not isinstance(value, dict):
        raise PseudoError(f"KEYS works on a map, but got {kind_of(value)}.")
    return list(value)


def same(a: Any, b: Any) -> bool:
    """== without Python's surprises: TRUE is not 1, and 1 == 1.0."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if is_number(a) and is_number(b):
        return a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    return a == b


def hashable(key: Any, line: int) -> Any:
    if isinstance(key, list | dict):
        raise PseudoError("A map's keys must be text or numbers.", line)
    return key


# --- entry points ------------------------------------------------------------------


def run_source(source: str) -> dict[str, Any]:
    """Run a program; returns its variables (functions included, callable)."""
    previous = sys.getrecursionlimit()
    sys.setrecursionlimit(max(previous, 20_000))
    try:
        return Interpreter().run(parse(source))
    except RecursionError:
        raise PseudoError("The program is nested too deeply to run.") from None
    finally:
        sys.setrecursionlimit(previous)


def run_file(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return run_source(f.read())


def trace_source(source: str, inputs: list[str]) -> dict:
    """Run a program step by step; returns {"steps": [...], "error": ..., "truncated": ...}.

    Each step is the line about to run, the variables of every active function at that
    moment (text in quotes), and how much of "output" had been shown by then.
    """
    interpreter = Interpreter(trace=True, inputs=inputs)
    result: dict[str, Any] = {"steps": interpreter.steps, "error": None, "truncated": False}
    sys.setrecursionlimit(20_000)
    try:
        interpreter.run(parse(source))
        interpreter.steps.append(  # the finished state: line 0 means "done"
            {"line": 0, "frames": interpreter.snapshot(), "out": interpreter.output_length}
        )
    except PseudoError as e:
        result["error"] = {"line": e.line, "message": e.message}
        interpreter.steps.append(
            {
                "line": e.line or 0,
                "frames": e.frames or interpreter.snapshot(),
                "out": interpreter.output_length,
            }
        )
    except TraceFull:
        result["truncated"] = True
    except RecursionError:
        result["error"] = {"line": None, "message": "The program is nested too deeply to run."}
    result["output"] = "".join(interpreter.output)
    return result


def excepthook(kind, error, tb) -> None:
    """Show a learner's mistake like Python shows its own, minus our internals."""
    if isinstance(error, PseudoError):
        if error.line:
            print(f'  File "main.pseudo", line {error.line}', file=sys.stderr)
        print(f"PseudoError: {error}", file=sys.stderr)
    else:
        sys.__excepthook__(kind, error, tb)


def main(argv: list[str]) -> int:
    if argv[:1] == ["--trace"]:
        with open(argv[1], encoding="utf-8") as f:
            source = f.read()
        inputs = sys.stdin.read().splitlines()
        print(json.dumps(trace_source(source, inputs)))
        return 0
    sys.excepthook = excepthook
    run_file(argv[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
