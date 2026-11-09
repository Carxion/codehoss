def test_small():
    from main import chunk_text

    got = chunk_text("one two three four five six seven", size=3, overlap=1)
    assert got == ["one two three", "three four five", "five six seven"], f"got {got}"
