"""Export a finished project as a zip: README plus code (and a Jupyter notebook)."""

from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import UTC, datetime

CELL_MARKER = re.compile(r"^# %%.*$", re.MULTILINE)


def to_ipynb(source: str) -> str:
    """Convert "# %%" percent-format Python into a Jupyter notebook (nbformat 4)."""
    parts = [part.strip("\n") for part in CELL_MARKER.split(source)]
    cells = [
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": part.splitlines(keepends=True),
        }
        for part in parts
        if part.strip()
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(notebook, indent=1)


def readme(item: dict, username: str) -> str:
    finished = datetime.fromtimestamp(item["completed_at"], UTC).strftime("%Y-%m-%d")
    code_file = "project.ipynb" if item["view"] == "notebook" else "main.py"
    checkpoints = "\n".join(f"{i}. {title}" for i, title in enumerate(item["checkpoints"], 1))
    skills = ", ".join(item["uses"]) or "Python"
    also = " (and as plain Python in `project.py`)" if item["view"] == "notebook" else ""
    return f"""# {item["title"]}

{item["summary"]}

Built by **{username}** on CodeHoss ({item["level"]} level), finished {finished}.
Skills: {skills}.

## The brief

{item["brief"].strip()}

## Checkpoints

{checkpoints}

## Running it

The code is in `{code_file}`{also}.
Files it reads from `/data/...` came from CodeHoss's datasets; point those paths at
your own copies to run it elsewhere. Code that uses `hoss_ai` ran on CodeHoss's model
picker; swap in a provider library such as `ollama` or `anthropic` to run it on its own.

To put it on GitHub or GitLab:

```bash
git init && git add . && git commit -m "{item["title"]}"
```
"""


def export_zip(item: dict, username: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", readme(item, username))
        if item["view"] == "notebook":
            archive.writestr("project.ipynb", to_ipynb(item["code"]))
            archive.writestr("project.py", item["code"])
        else:
            archive.writestr("main.py", item["code"])
    return buffer.getvalue()
