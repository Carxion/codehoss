# %%
import math


def rough_tokens(text):
    return math.ceil(len(text.split()) * 4 / 3)


def cost(text, dollars_per_million):
    return rough_tokens(text) * dollars_per_million / 1_000_000


# %%
rough_tokens("one two three"), cost("word " * 1000, 3.0)
