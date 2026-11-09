def test_add():
    from main import add_expense

    expenses = []
    add_expense(expenses, "Lunch", "12.5", " Food ")
    assert expenses == [{"description": "Lunch", "amount": 12.5, "category": "food"}], expenses
