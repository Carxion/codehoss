import dojo_ai


def test_calls_model_with_system():
    from main import CHUNKS, SYSTEM, answer

    dojo_ai.fake(chat=lambda messages, **kw: "30 days")

    assert answer("How long do I have to return a bike?", CHUNKS) == "30 days"
    assert dojo_ai.calls[-1]["system"] == SYSTEM
