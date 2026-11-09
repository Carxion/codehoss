# %%
import matplotlib.pyplot as plt
import pandas as pd


def load_weather(path):
    df = pd.read_csv(path)
    # TODO: parse the date column as dates
    # TODO: drop duplicate rows, and rows missing temp_max_c or temp_min_c
    # TODO: add temp_mean_c, the average of temp_max_c and temp_min_c
    return df  # TODO: reset the index


# %%
weather = load_weather("/data/weather.csv")
weather.head()
