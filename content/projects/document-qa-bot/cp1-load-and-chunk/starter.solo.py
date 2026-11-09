# %%
from pathlib import Path

import dojo_ai

SYSTEM = (
    "Answer using only the context. Mention the [source] you used. "
    "If the answer isn't in the context, say you don't know."
)


# Checkpoint 1: Load and chunk. Build it your way.
