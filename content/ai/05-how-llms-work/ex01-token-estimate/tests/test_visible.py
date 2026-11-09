def test_rough_tokens():
    from main import rough_tokens

    assert rough_tokens("one two three") == 4
