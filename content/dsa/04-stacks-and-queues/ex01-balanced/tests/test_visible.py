def test_examples():
    from main import is_balanced

    assert is_balanced("{[()()]}") is True
    assert is_balanced("([)]") is False
