import hoss_ai


def test_answer_and_sources():
    from main import SYSTEM, answer

    hoss_ai.fake(chat=lambda messages, **kw: "Within 30 days. [returns.md]")
    chunks = [
        {"source": "returns.md", "text": "return within 30 days"},
        {"source": "x.md", "text": "other"},
    ]
    got = answer("return days", chunks, k=1)
    assert got == {"answer": "Within 30 days. [returns.md]", "sources": ["returns.md"]}, got
    assert hoss_ai.calls[-1]["system"] == SYSTEM
