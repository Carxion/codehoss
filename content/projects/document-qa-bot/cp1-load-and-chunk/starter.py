# %%
from pathlib import Path

import hoss_ai

SYSTEM = (
    "Answer using only the context. Mention the [source] you used. "
    "If the answer isn't in the context, say you don't know."
)


def load_documents(folder):
    docs = []
    for path in sorted(Path(folder).glob("*.md")):
        pass  # TODO: append {"source": path.name, "text": the file's text}
    return docs


def chunk_documents(docs, size=40, overlap=10):
    chunks = []
    for doc in docs:
        words = doc["text"].split()
        # TODO: slide a window of `size` words, moving `size - overlap` each time,
        #   appending {"source": doc["source"], "text": the joined words}
    return chunks


# %%
CHUNKS = chunk_documents(load_documents("/data/handbook"))
len(CHUNKS), CHUNKS[:1]
