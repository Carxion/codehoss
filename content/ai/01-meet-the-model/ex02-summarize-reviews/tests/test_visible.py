import hoss_ai


def test_one_call():
    from main import summarize_reviews

    hoss_ai.fake(chat=lambda messages, **kw: "Mostly positive.")

    assert summarize_reviews(["Good", "Bad"]) == "Mostly positive."
    assert len(hoss_ai.calls) == 1, f"Call the model once, not {len(hoss_ai.calls)} times"
