# %%
import pandas as pd

df = pd.read_csv("/data/movies.csv")

# %%
rating_stats = {
    "mean": round(df["rating"].mean(), 2),
    "median": round(df["rating"].median(), 2),
    "std": round(df["rating"].std(), 2),
}
votes_gross_corr = round(df["votes"].corr(df["gross_millions"]), 3)
rating_stats, votes_gross_corr
