# %%
from pathlib import Path

import hoss_ai

SYSTEM = "Answer using only the context. If the answer isn't there, say you don't know."
CHUNKS = []
for path in sorted(Path("/data/handbook").glob("*.md")):
    words = path.read_text().split()
    CHUNKS += [" ".join(words[i : i + 40]) for i in range(0, len(words), 30)]


def answer(question, chunks, k=3):
    query, *vectors = hoss_ai.embed([question] + chunks)
    ranked = sorted(
        zip(chunks, vectors),
        key=lambda pair: hoss_ai.cosine_similarity(query, pair[1]),
        reverse=True,
    )
    top = [chunk for chunk, _ in ranked[:k]]
    prompt = "Context:\n" + "\n\n".join(top) + f"\n\nQuestion: {question}"
    return hoss_ai.chat(prompt, system=SYSTEM)


# %%
answer("How long do I have to return a bike?", CHUNKS)
