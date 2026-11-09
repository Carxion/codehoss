def test_edges():
    from main import chunk_text

    assert chunk_text("") == []
    assert chunk_text("a b", size=5, overlap=2) == ["a b"]
    words = " ".join(f"w{i}" for i in range(10))
    assert chunk_text(words, size=4, overlap=0) == ["w0 w1 w2 w3", "w4 w5 w6 w7", "w8 w9"]
    assert chunk_text(words, size=4, overlap=2)[-1] == "w6 w7 w8 w9"
