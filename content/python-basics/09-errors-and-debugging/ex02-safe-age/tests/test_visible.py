def test_valid_age():
    from main import parse_age

    assert parse_age("42") == 42
