def test_divide():
    from main import answer

    assert answer("8 / 2") == "= 4", f"answer('8 / 2') gave {answer('8 / 2')!r}"
