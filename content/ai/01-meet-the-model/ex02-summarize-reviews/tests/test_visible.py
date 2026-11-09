import dojo_ai


def test_one_call():
    from main import summarize_reviews

    dojo_ai.fake(chat=lambda messages, **kw: "Mostly positive.")

    assert summarize_reviews(["Good", "Bad"]) == "Mostly positive."
    assert len(dojo_ai.calls) == 1, f"Call the model once, not {len(dojo_ai.calls)} times"
