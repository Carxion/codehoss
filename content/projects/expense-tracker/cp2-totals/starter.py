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
    # TODO: add up every expense's amount, rounded to 2 decimals
    return 0


def totals_by_category(expenses):
    totals = {}
    # TODO: for each expense, add its amount to totals[its category]
    # TODO: return the totals with categories in alphabetical order, rounded to 2 decimals
    return totals

