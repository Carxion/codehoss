# %%
import math


def rough_tokens(text):
    return math.ceil(len(text.split()) * 4 / 3)


def total_tokens(messages):
    # TODO
    return 0


def trim_to_fit(messages, limit):
    # TODO
    return messages
