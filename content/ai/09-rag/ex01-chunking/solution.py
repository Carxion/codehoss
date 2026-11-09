# %%
def chunk_text(text, size=40, overlap=10):
    words = text.split()
    step = size - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
    return chunks


# %%
chunk_text("one two three four five six seven", size=3, overlap=1)
