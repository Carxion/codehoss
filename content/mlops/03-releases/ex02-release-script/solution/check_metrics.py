"""Quality gate: exit with an error if the model isn't good enough to ship."""

import json
import os
import sys

MAX_MAE = float(os.environ.get("MAX_MAE", "25000"))

with open("model/metrics.json") as f:
    metrics = json.load(f)
if metrics["mae"] > MAX_MAE:
    print(f"FAIL: MAE {metrics['mae']:,.0f} is above the limit of {MAX_MAE:,.0f}")
    sys.exit(1)
print(f"metrics OK: MAE {metrics['mae']:,.0f} (limit {MAX_MAE:,.0f})")
