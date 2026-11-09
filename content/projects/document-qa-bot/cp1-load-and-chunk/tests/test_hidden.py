def test_cp1_chunks():
    from main import chunk_documents

    docs = [
        {"source": "a.md", "text": " ".join(f"w{i}" for i in range(10))},
        {"source": "b.md", "text": "x y"},
    ]
    got = chunk_documents(docs, size=4, overlap=1)
    assert [c["text"] for c in got] == ["w0 w1 w2 w3", "w3 w4 w5 w6", "w6 w7 w8 w9", "x y"], got
    assert [c["source"] for c in got] == ["a.md", "a.md", "a.md", "b.md"]
