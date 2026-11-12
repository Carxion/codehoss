import hoss_ai


def scripted(*replies):
    queue = list(replies)
    return lambda messages, **kw: queue.pop(0)


def test_full_conversation():
    hoss_ai.fake(
        chat=scripted(
            '{"tool": "add", "args": {"a": 3, "b": 4}}',
            "oops, not json",
            '{"tool": "multiply", "args": {"a": 7, "b": 6}}',
            '{"answer": "42"}',
        )
    )
    from main import SYSTEM, agent

    assert agent("What is (3 + 4) times 6?") == "42"
    last = hoss_ai.calls[-1]
    assert last["system"] == SYSTEM and last["json"] is True
    assert [m["role"] for m in last["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
    ]
    assert last["messages"][4] == {"role": "user", "content": "Please reply with valid JSON."}
    assert last["messages"][6] == {"role": "user", "content": "Tool result: 42"}


def test_step_limit():
    from main import agent

    hoss_ai.fake(chat=lambda messages, **kw: '{"tool": "add", "args": {"a": 1, "b": 1}}')

    assert agent("loop forever", max_steps=3) == "I couldn't finish."
    assert len(hoss_ai.calls) == 3, "Stop after max_steps calls"
