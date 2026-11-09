def test_round_trip(tmp_path):
    from main import add_expense, load, save

    expenses = []
    add_expense(expenses, "Lunch", 12.5, "food")
    save(expenses, tmp_path / "e.json")
    assert load(tmp_path / "e.json") == expenses
