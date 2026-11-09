import csv


def total_sales(path):
    total = 0.0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            total += float(row["amount"])
    return total


def best_seller(path):
    totals = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            totals[row["item"]] = totals.get(row["item"], 0) + float(row["amount"])
    return max(totals, key=totals.get)
