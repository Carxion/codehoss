def test_cp1_format():
    from main import add_expense, format_expense

    expenses = []
    add_expense(expenses, "Bus pass", 40, "Transport")
    add_expense(expenses, "Coffee", 3.456, "food")
    assert format_expense(expenses[0]) == "Bus pass: $40.00 (transport)"
    assert expenses[1]["amount"] == 3.46
