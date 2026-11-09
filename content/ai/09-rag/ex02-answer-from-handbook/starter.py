# %%
from pathlib import Path

import dojo_ai

SYSTEM = "Answer using only the context. If the answer isn't there, say you don't know."
CHUNKS = []
for path in sorted(Path("/data/handbook").glob("*.md")):
    words = path.read_text().split()
    CHUNKS += [" ".join(words[i : i + 40]) for i in range(0, len(words), 30)]


def answer(question, chunks, k=3):
    # TODO
    return ""


# %%
answer("How long do I have to return a bike?", CHUNKS)
