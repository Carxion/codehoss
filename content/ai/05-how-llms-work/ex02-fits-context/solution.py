# %%
import math


def rough_tokens(text):
    return math.ceil(len(text.split()) * 4 / 3)


def total_tokens(messages):
    return sum(rough_tokens(m["content"]) for m in messages)


def trim_to_fit(messages, limit):
    kept = list(messages)
    while kept and total_tokens(kept) > limit:
        kept.pop(0)
    return kept
