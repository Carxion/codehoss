def test_trim():
    from main import trim_to_fit

    messages = [
        {"role": "user", "content": "a " * 30},
        {"role": "assistant", "content": "b " * 30},
        {"role": "user", "content": "c " * 3},
    ]
    kept = trim_to_fit(messages, 50)
    assert kept == messages[1:], "Drop the oldest messages first"
    assert len(messages) == 3, "Don't change the original list"
    assert trim_to_fit(messages, 1000) == messages
