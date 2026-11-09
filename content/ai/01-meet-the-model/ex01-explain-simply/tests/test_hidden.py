import dojo_ai


def test_prompt():
    from main import explain_simply

    dojo_ai.fake(chat=lambda messages, **kw: "ok")

    explain_simply("photosynthesis")
    assert dojo_ai.calls[-1]["messages"] == [{"role": "user", "content": "Explain photosynthesis."}]
