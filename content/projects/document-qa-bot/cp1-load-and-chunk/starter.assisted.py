# %%
from pathlib import Path

import hoss_ai

SYSTEM = (
    "Answer using only the context. Mention the [source] you used. "
    "If the answer isn't in the context, say you don't know."
)


def load_documents(folder):
    """[{"source": filename, "text": ...}] for every .md file, sorted by name."""
    raise NotImplementedError


def chunk_documents(docs, size=40, overlap=10):
    """Overlapping word windows per document, as [{"source", "text"}]."""
    raise NotImplementedError


# %%
CHUNKS = chunk_documents(load_documents("/data/handbook"))
len(CHUNKS), CHUNKS[:1]
