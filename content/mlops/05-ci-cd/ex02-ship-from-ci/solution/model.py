"""A tiny linear-regression model in plain Python, so it runs anywhere (no numpy)."""

import csv

FEATURES = ["sqft", "bedrooms", "age"]


def load_rows(path):
    with open(path, newline="") as f:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]


def fit(rows, features=FEATURES, target="price"):
    """Least squares: solve (X^T X) w = X^T y. weights[0] is the intercept."""
    xs = [[1.0] + [r[f] for f in features] for r in rows]
    ys = [r[target] for r in rows]
    n = len(xs[0])
    a = [
        [sum(x[i] * x[j] for x in xs) for j in range(n)] + [sum(x[i] * y for x, y in zip(xs, ys))]
        for i in range(n)
    ]
    for col in range(n):  # Gauss-Jordan elimination
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(n):
            if r != col:
                factor = a[r][col] / a[col][col]
                a[r] = [v - factor * p for v, p in zip(a[r], a[col])]
    return [a[i][n] / a[i][i] for i in range(n)]


def predict(weights, features, values):
    return weights[0] + sum(w * values[f] for w, f in zip(weights[1:], features))


def mean_absolute_error(weights, features, rows, target="price"):
    return sum(abs(predict(weights, features, r) - r[target]) for r in rows) / len(rows)
