def test_load():
    from main import load_documents

    docs = load_documents("/data/handbook")
    assert [d["source"] for d in docs][:2] == ["contact.md", "ebikes.md"]
