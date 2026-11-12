import hoss_ai


def test_redacts_before_sending():
    from main import safe_chat

    hoss_ai.fake(chat=lambda messages, **kw: "Soon!")

    assert safe_chat("I'm ada@lumen.example, where is my bike?") == "Soon!"
    assert hoss_ai.calls[-1]["messages"][-1]["content"] == "I'm [EMAIL], where is my bike?"
