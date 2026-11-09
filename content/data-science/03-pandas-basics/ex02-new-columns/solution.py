# %%
import pandas as pd

df = pd.read_csv("/data/movies.csv")

# %%
df["runtime_hours"] = (df["runtime"] / 60).round(2)
df["is_long"] = df["runtime"] > 120

long_count = df["is_long"].sum()
df.head()
