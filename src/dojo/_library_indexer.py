"""Runs inside a sandbox image: introspect modules for the Library Explorer.

Usage: python - <module> [<module> ...]   (this file on stdin); prints JSON.
Standard library only, since it runs in whatever image the module uses.
"""

import importlib
import inspect
import json
import sys

MAX_DOC = 400


def summary(obj):
    doc = inspect.getdoc(obj) or ""
    return doc.split("\n\n")[0].strip()[:MAX_DOC]


def signature(obj):
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return ""


def kind_of(obj):
    if inspect.isclass(obj):
        return "exception" if issubclass(obj, BaseException) else "class"
    if callable(obj):
        return "function"
    return "value"


def describe(name, obj, depth=0):
    kind = kind_of(obj)
    entry = {"name": name, "kind": kind}
    if kind == "value":
        entry["doc"] = repr(obj)[:80]
        return entry
    entry["signature"] = signature(obj) if kind != "exception" else ""
    entry["doc"] = summary(obj)
    if kind == "class" and depth == 0:
        # dir(), not vars(): most everyday methods are inherited (DataFrame.head lives on
        # a base class).
        members = []
        for member in dir(obj):
            if member.startswith("_"):
                continue
            try:
                value = getattr(obj, member)
            except Exception:  # noqa: BLE001
                continue
            if callable(value):
                members.append(describe(member, value, depth + 1))
        entry["members"] = members
    return entry


def index(module_name):
    try:
        module = importlib.import_module(module_name)
    except Exception as e:  # noqa: BLE001 - report any import failure in the index
        return {"name": module_name, "error": str(e), "members": []}
    names = getattr(module, "__all__", None) or [n for n in dir(module) if not n.startswith("_")]
    members = []
    for name in sorted(names):
        try:
            # Some libraries raise on access, e.g. scikit-learn's experimental features.
            obj = getattr(module, name)
            if inspect.ismodule(obj):
                continue
            members.append(describe(name, obj))
        except Exception:  # noqa: BLE001 - skip anything that can't be introspected
            continue
    return {"name": module_name, "doc": summary(module), "members": members}


print(json.dumps([index(name) for name in sys.argv[1:]]))
