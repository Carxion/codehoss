import dojo_ai


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
        return [dojo_ai.simple_embed(t) for t in texts]

    dojo_ai.fake(embed=counting)
    chunks = [{"source": "a", "text": "red apples"}, {"source": "b", "text": "blue cars"}]
    assert retrieve("apples", chunks, k=1) == [chunks[0]]
    assert len(calls) == 1


def test_cp3_prompt():
    from main import answer

    dojo_ai.fake(chat=lambda messages, **kw: "ok")
    chunks = [
        {"source": "b.md", "text": "alpha beta"},
        {"source": "a.md", "text": "alpha gamma"},
        {"source": "c.md", "text": "zzz"},
    ]
    got = answer("alpha", chunks, k=2)
    prompt = dojo_ai.calls[-1]["messages"][-1]["content"]
    assert prompt.startswith("Context:\n[") and prompt.endswith("\n\nQuestion: alpha"), prompt
    assert "[a.md] alpha gamma" in prompt and "[b.md] alpha beta" in prompt and "zzz" not in prompt
    assert got["sources"] == ["a.md", "b.md"]


def test_cp4_partial():
    from main import evaluate

    dojo_ai.fake(chat=lambda messages, **kw: "Express costs $49")
    chunks = [
        {"source": "shipping.md", "text": "express shipping costs"},
        {"source": "warranty.md", "text": "battery years"},
    ]
    cases = [
        {
            "question": "express shipping costs",
            "keywords": ["$49", "2 business days"],
            "source": "shipping.md",
        },
        {"question": "battery years", "keywords": ["3 years"], "source": "returns.md"},
    ]
    got = evaluate(cases, chunks)
    assert got == {"keyword_score": 0.25, "source_accuracy": 0.5}, got
