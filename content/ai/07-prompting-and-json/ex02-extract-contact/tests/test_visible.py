import hoss_ai


def test_good_reply():
    from main import extract_contact

    hoss_ai.fake(chat=lambda messages, **kw: '{"name": "Ada", "email": "ada@x.org"}')

    assert extract_contact("Ada, ada@x.org") == {"name": "Ada", "email": "ada@x.org"}
    assert hoss_ai.calls[-1]["json"] is True, "Ask for JSON with json=True"
