import json


def add_expense(expenses, description, amount, category):
    expenses.append(
        {
            "description": description,
            "amount": round(float(amount), 2),
            "category": category.strip().lower(),
        }
    )


def format_expense(expense):
    return f"{expense['description']}: ${expense['amount']:.2f} ({expense['category']})"


def total(expenses):
    """Sum of all amounts, rounded to 2 decimals."""
    raise NotImplementedError


def totals_by_category(expenses):
    """{category: total} in alphabetical order, totals rounded to 2 decimals."""
    raise NotImplementedError

