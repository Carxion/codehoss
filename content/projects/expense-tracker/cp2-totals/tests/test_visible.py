def test_total():
    from main import add_expense, total

    expenses = []
    add_expense(expenses, "a", 1.1, "x")
    add_expense(expenses, "b", 2.2, "y")
    assert total(expenses) == 3.3
