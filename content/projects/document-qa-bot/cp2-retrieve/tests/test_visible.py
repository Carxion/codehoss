def test_finds_shipping():
    from main import chunk_documents, load_documents, retrieve

    chunks = chunk_documents(load_documents("/data/handbook"))
    # The built-in embedding only matches shared words, so ask with the handbook's words.
    top = retrieve("express shipping costs and business days", chunks, k=1)
    assert top[0]["source"] == "shipping.md", top
