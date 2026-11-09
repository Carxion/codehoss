def test_keeps_history_unchanged():
    from main import build_messages

    history = [{"role": "user", "content": "A"}, {"role": "assistant", "content": "B"}]
    result = build_messages(history, "C")
    assert result == history + [{"role": "user", "content": "C"}]
    assert len(history) == 2, "Don't change history"
    assert result is not history
