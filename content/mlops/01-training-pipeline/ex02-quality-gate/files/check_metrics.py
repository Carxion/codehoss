"""Quality gate: exit with an error if the model isn't good enough to ship."""

import os

MAX_MAE = float(os.environ.get("MAX_MAE", "25000"))

# TODO: read model/metrics.json. If its "mae" is above MAX_MAE, print a line starting
# with FAIL and exit with status 1 (sys.exit(1)); otherwise print a line starting with
# "metrics OK".
