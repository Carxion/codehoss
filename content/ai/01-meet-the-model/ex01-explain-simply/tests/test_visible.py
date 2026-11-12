import hoss_ai


def test_uses_system_prompt():
    from main import SYSTEM, explain_simply

    hoss_ai.fake(chat=lambda messages, **kw: "  Things fall down.  ")

    assert explain_simply("gravity") == "Things fall down."
    assert hoss_ai.calls[-1]["system"] == SYSTEM, "Pass SYSTEM as the system prompt"
