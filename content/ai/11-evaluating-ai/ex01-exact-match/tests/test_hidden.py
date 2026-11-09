def test_normalised():
    from main import exact_match

    assert (
        exact_match([" Positive", "NEGATIVE ", "neutral"], ["positive", "negative", "positive"])
        == 2 / 3
    )
    assert exact_match([], []) == 0.0
