def test_has_digit(run_program):
    has_digit = run_program().vars.get("has_digit")
    assert callable(has_digit), "Keep the FUNCTION called has_digit"
    assert has_digit("abc1") is True and has_digit("9") is True
    assert has_digit("abc") is False and has_digit("") is False


def test_strong(run_program):
    strong = run_program().vars.get("strong")
    assert strong("sun5") is False, "Too short, even with a digit"
    assert strong("12345678") is True
    assert strong("correct horse battery staple 2") is True
    assert strong("abcdefgh") is False
