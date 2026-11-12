import hoss_ai


def test_cp1_chunks():
    from main import chunk_documents

    docs = [
        {"source": "a.md", "text": " ".join(f"w{i}" for i in range(10))},
        {"source": "b.md", "text": "x y"},
    ]
    got = chunk_documents(docs, size=4, overlap=1)
    assert [c["text"] for c in got] == ["w0 w1 w2 w3", "w3 w4 w5 w6", "w6 w7 w8 w9", "x y"], got
    assert [c["source"] for c in got] == ["a.md", "a.md", "a.md", "b.md"]


def test_cp2_one_embed_call():
    from main import retrieve

    calls = []

    def counting(texts):
        calls.append(texts)
        return [hoss_ai.simple_embed(t) for t in texts]

    hoss_ai.fake(embed=counting)
    chunks = [{"source": "a", "text": "red apples"}, {"source": "b", "text": "blue cars"}]
    assert retrieve("apples", chunks, k=1) == [chunks[0]]
    assert len(calls) == 1
