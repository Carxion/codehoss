"""Train the house-price model and save it, with its metrics, in model/."""

import os

from model import FEATURES, fit, load_rows, mean_absolute_error

VERSION = os.environ.get("MODEL_VERSION", "1.0.0")

rows = load_rows("data/houses.csv")
test = rows[::5]  # every 5th row is held back to test the model on houses it hasn't seen
train = [r for i, r in enumerate(rows) if i % 5]
weights = fit(train, FEATURES)
mae = mean_absolute_error(weights, FEATURES, test)
print(f"model {VERSION}: MAE {mae:,.0f} on {len(test)} test rows")

# TODO: save the model and its metrics in a folder called model/:
#   model/model.json    {"version": VERSION, "features": FEATURES, "weights": weights}
#   model/metrics.json  {"version": VERSION, "mae": <mae rounded to 2 places>,
#                        "train_rows": <how many>, "test_rows": <how many>}
