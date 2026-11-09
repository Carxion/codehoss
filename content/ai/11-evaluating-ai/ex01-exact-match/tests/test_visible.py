def test_basic():
    from main import exact_match

    assert exact_match(["yes", "no"], ["yes", "yes"]) == 0.5
