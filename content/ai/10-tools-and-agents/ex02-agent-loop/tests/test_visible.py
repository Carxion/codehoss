import dojo_ai


def scripted(*replies):
    queue = list(replies)
    return lambda messages, **kw: queue.pop(0)


def test_uses_a_tool_then_answers():
    from main import agent

    dojo_ai.fake(chat=scripted('{"tool": "add", "args": {"a": 3, "b": 4}}', '{"answer": "7"}'))

    assert agent("What is 3 + 4?") == "7"
    assert dojo_ai.calls[1]["messages"][-1] == {"role": "user", "content": "Tool result: 7"}
