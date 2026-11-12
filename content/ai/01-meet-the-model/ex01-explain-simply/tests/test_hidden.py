import hoss_ai


def test_prompt():
    from main import explain_simply

    hoss_ai.fake(chat=lambda messages, **kw: "ok")

    explain_simply("photosynthesis")
    assert hoss_ai.calls[-1]["messages"] == [{"role": "user", "content": "Explain photosynthesis."}]
