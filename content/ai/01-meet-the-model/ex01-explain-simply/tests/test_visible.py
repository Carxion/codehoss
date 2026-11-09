import dojo_ai


def test_uses_system_prompt():
    from main import SYSTEM, explain_simply

    dojo_ai.fake(chat=lambda messages, **kw: "  Things fall down.  ")

    assert explain_simply("gravity") == "Things fall down."
    assert dojo_ai.calls[-1]["system"] == SYSTEM, "Pass SYSTEM as the system prompt"
