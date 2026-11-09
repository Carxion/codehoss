def test_adds_user_message():
    from main import build_messages

    assert build_messages([], "Hi") == [{"role": "user", "content": "Hi"}]
