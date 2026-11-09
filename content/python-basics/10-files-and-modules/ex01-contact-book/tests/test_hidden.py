def test_save_then_load(tmp_path):
    from main import add_contact, load_contacts, save_contacts

    path = tmp_path / "contacts.json"
    book = {}
    add_contact(book, "Ada", "555-0101")
    add_contact(book, "Alan", "555-0199")
    save_contacts(book, path)
    assert path.exists(), "save_contacts should create the file"
    assert load_contacts(path) == book


def test_missing_file_gives_empty_book(tmp_path):
    from main import load_contacts

    assert load_contacts(tmp_path / "nope.json") == {}
