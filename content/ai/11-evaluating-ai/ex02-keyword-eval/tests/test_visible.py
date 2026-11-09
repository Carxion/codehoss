def test_keyword_score():
    from main import keyword_score

    assert keyword_score("You have 30 days.", ["30", "Days"]) == 1.0
