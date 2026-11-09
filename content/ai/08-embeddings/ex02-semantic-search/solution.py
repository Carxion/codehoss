# %%
import dojo_ai

DOCS = [
    "Our bikes ship free and arrive in 5 to 8 days.",
    "Frames have a lifetime warranty.",
    "E-bike batteries charge in about 4 hours.",
]


def search(query, docs, k=2):
    query_vector, *doc_vectors = dojo_ai.embed([query] + docs)
    scored = [
        (doc, dojo_ai.cosine_similarity(query_vector, v)) for doc, v in zip(docs, doc_vectors)
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [doc for doc, _ in scored[:k]]


# %%
search("how long does charging take", DOCS, k=1)
