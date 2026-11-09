"""Runs a try-it step: learner code, then the step's check, in one namespace.

Usage: python _tryit_runner.py <code_file> <check_file>
Exit code 0 means the check passed.
"""

import builtins
import contextlib
import io
import sys

code = open(sys.argv[1], encoding="utf-8").read()
check = open(sys.argv[2], encoding="utf-8").read()

# Notebook code may call display(); here it does nothing.
builtins.display = lambda *args, **kwargs: None
namespace = {"__name__": "__main__"}
buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    exec(compile(code, "main.py", "exec"), namespace)
namespace["_output"] = buffer.getvalue()
exec(compile(check, "check", "exec"), namespace)
