# %%
from pathlib import Path

import dojo_ai

SYSTEM = (
    "Answer using only the context. Mention the [source] you used. "
    "If the answer isn't in the context, say you don't know."
)


def load_documents(folder):
    return [
        {"source": path.name, "text": path.read_text(encoding="utf-8")}
        for path in sorted(Path(folder).glob("*.md"))
    ]


def chunk_documents(docs, size=40, overlap=10):
    chunks = []
    for doc in docs:
        words = doc["text"].split()
        for start in range(0, len(words), size - overlap):
            chunks.append({"source": doc["source"], "text": " ".join(words[start : start + size])})
            if start + size >= len(words):
                break
    return chunks


# %%
CHUNKS = chunk_documents(load_documents("/data/handbook"))
len(CHUNKS), CHUNKS[0]


# Checkpoint 2: Retrieve. Build it your way.
