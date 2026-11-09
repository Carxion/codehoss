def test_total():
    from main import total_tokens

    messages = [
        {"role": "user", "content": "one two three"},
        {"role": "assistant", "content": "four"},
    ]
    assert total_tokens(messages) == 4 + 2
