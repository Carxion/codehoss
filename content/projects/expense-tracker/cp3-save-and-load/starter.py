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
    return round(sum(e["amount"] for e in expenses), 2)


def totals_by_category(expenses):
    totals = {}
    for e in expenses:
        totals[e["category"]] = totals.get(e["category"], 0) + e["amount"]
    return {category: round(totals[category], 2) for category in sorted(totals)}


def save(expenses, path):
    # TODO: open path for writing and json.dump the list into it
    pass


def load(path):
    # TODO: open path and json.load it; if the file doesn't exist, return []
    return []

