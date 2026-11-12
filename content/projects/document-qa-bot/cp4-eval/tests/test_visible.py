import hoss_ai


def test_perfect_bot():
    from main import evaluate

    hoss_ai.fake(chat=lambda messages, **kw: "It is 30 days")
    chunks = [{"source": "returns.md", "text": "return days"}]
    cases = [{"question": "return days", "keywords": ["30"], "source": "returns.md"}]
    assert evaluate(cases, chunks) == {"keyword_score": 1.0, "source_accuracy": 1.0}
