import hoss_ai


def test_prompt_format():
    from main import summarize_reviews

    hoss_ai.fake(chat=lambda messages, **kw: "x")

    summarize_reviews(["Fast delivery", "Squeaky brakes", "Comfy seat"])
    expected = "Summarize these reviews in one sentence:\n1. Fast delivery\n2. Squeaky brakes\n3. Comfy seat"
    got = hoss_ai.calls[-1]["messages"][-1]["content"]
    assert got == expected, f"The prompt was:\n{got}"
