# %%
import matplotlib.pyplot as plt
import pandas as pd


def load_weather(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.drop_duplicates().dropna(subset=["temp_max_c", "temp_min_c"])
    df["temp_mean_c"] = (df["temp_max_c"] + df["temp_min_c"]) / 2
    return df.reset_index(drop=True)


# %%
weather = load_weather("/data/weather.csv")
weather.head()


# %%
def monthly_summary(df):
    df = df.assign(month=df["date"].dt.month)
    # TODO: group by city and month; average temp_mean_c and total precip_mm
    #   name the results avg_temp_c and total_precip_mm
    # TODO: round to 1 decimal and reset the index
    return df


# %%
summary = monthly_summary(weather)
summary.head(12)
