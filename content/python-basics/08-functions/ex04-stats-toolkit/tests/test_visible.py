def test_mean():
    from main import mean

    assert mean(2, 4, 9) == 5.0, f"mean(2, 4, 9) gave {mean(2, 4, 9)!r}"
