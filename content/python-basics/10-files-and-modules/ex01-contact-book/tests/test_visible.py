def test_add_contact():
    from main import add_contact

    book = {}
    add_contact(book, "Ada", "555-0101")
    assert book == {"Ada": "555-0101"}, f"book is {book}"
