import dojo_ai


def scripted(*replies):
    queue = list(replies)
    return lambda messages, **kw: queue.pop(0)


def test_retries_once():
    from main import extract_contact

    dojo_ai.fake(chat=scripted("Sure! Here you go", '{"name": "Ada", "email": "a@x.org"}'))

    assert extract_contact("Ada") == {"name": "Ada", "email": "a@x.org"}
    assert len(dojo_ai.calls) == 2


def test_gives_up_after_two():
    from main import extract_contact

    dojo_ai.fake(chat=scripted('{"name": "Ada"}', "not json", '{"name": "A", "email": "e"}'))

    assert extract_contact("Ada") is None
    assert len(dojo_ai.calls) == 2, "Ask at most twice"


def test_uses_prompt():
    from main import PROMPT, extract_contact

    dojo_ai.fake(chat=lambda messages, **kw: '{"name": "N", "email": "E"}')

    extract_contact("text here")
    assert dojo_ai.calls[-1]["messages"][-1]["content"] == PROMPT.format(text="text here")
