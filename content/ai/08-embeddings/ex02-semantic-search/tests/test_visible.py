def test_finds_battery_doc():
    from main import DOCS, search

    assert search("batteries charge", DOCS, k=1) == [DOCS[2]]
