"""Train the house-price model and save it, with its metrics, in model/."""

import json
import os
from pathlib import Path

from model import FEATURES, fit, load_rows, mean_absolute_error

VERSION = os.environ.get("MODEL_VERSION", "1.0.0")

rows = load_rows("data/houses.csv")
test = rows[::5]  # every 5th row is held back to test the model on houses it hasn't seen
train = [r for i, r in enumerate(rows) if i % 5]
weights = fit(train, FEATURES)
mae = mean_absolute_error(weights, FEATURES, test)
print(f"model {VERSION}: MAE {mae:,.0f} on {len(test)} test rows")

out = Path("model")
out.mkdir(exist_ok=True)
model = {"version": VERSION, "features": FEATURES, "weights": weights}
metrics = {
    "version": VERSION,
    "mae": round(mae, 2),
    "train_rows": len(train),
    "test_rows": len(test),
}
(out / "model.json").write_text(json.dumps(model, indent=2))
(out / "metrics.json").write_text(json.dumps(metrics, indent=2))
