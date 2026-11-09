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
    with open(path, "w") as f:
        json.dump(expenses, f, indent=2)


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def main(path="expenses.json"):
    expenses = load(path)
    while True:
        command = input("> ").strip()
        parts = command.split(maxsplit=3)
        if command == "quit":
            # TODO: save, then stop the loop
            break
        # TODO: elif add: add_expense(expenses, description, amount, category); print("Added.")
        # TODO: elif list: print each expense, or "No expenses yet."
        # TODO: elif report: each "category: $total", then "Total: $total"
        # TODO: else: print("Commands: add, list, report, quit")


if __name__ == "__main__":
    main()
