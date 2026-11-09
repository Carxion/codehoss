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


def retrieve(question, chunks, k=3):
    query, *vectors = dojo_ai.embed([question] + [c["text"] for c in chunks])
    ranked = sorted(
        zip(chunks, vectors), key=lambda pair: dojo_ai.cosine_similarity(query, pair[1]), reverse=True
    )
    return [chunk for chunk, _ in ranked[:k]]


# %%
[c["source"] for c in retrieve("How long is the warranty on batteries?", CHUNKS)]


def answer(question, chunks, k=3):
    top = retrieve(question, chunks, k)
    context = "\n\n".join(f"[{c['source']}] {c['text']}" for c in top)
    reply = dojo_ai.chat(f"Context:\n{context}\n\nQuestion: {question}", system=SYSTEM)
    return {"answer": reply, "sources": sorted({c["source"] for c in top})}


# %%
answer("Can I return a custom-painted bike?", CHUNKS)


def evaluate(cases, chunks):
    keyword_scores, hits = [], []
    for case in cases:
        result = answer(case["question"], chunks)
        # TODO: keyword score (share of case["keywords"] in the answer, any case)
        # TODO: source hit (1 if case["source"] is in result["sources"])
    return {"keyword_score": 0.0, "source_accuracy": 0.0}  # TODO: averages, 3 decimals


CASES = [
    {"question": "How many days do I have to return a bike?", "keywords": ["30"], "source": "returns.md"},
    {"question": "How long are batteries covered?", "keywords": ["3 years", "800"], "source": "warranty.md"},
    {"question": "What does express shipping cost?", "keywords": ["$49"], "source": "shipping.md"},
]

# %%
evaluate(CASES, CHUNKS)
