# %%
import matplotlib.pyplot as plt
import pandas as pd


def load_weather(path):
    """Read the CSV; parse dates; drop duplicates and missing temps; add temp_mean_c."""
    raise NotImplementedError


# %%
weather = load_weather("/data/weather.csv")
weather.head()
