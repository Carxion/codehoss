def test_summarize():
    from main import summarize

    assert summarize([2, 6, 3]) == {"min": 2, "max": 6, "mean": 3.67}
