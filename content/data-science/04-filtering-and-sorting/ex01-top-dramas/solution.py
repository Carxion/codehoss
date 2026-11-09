# %%
import pandas as pd

df = pd.read_csv("/data/movies.csv")

# %%
dramas = df[(df["genre"] == "Drama") & (df["year"] >= 2000)]
top_dramas = dramas.sort_values(["rating", "title"], ascending=[False, True]).head(5)[
    ["title", "year", "rating"]
]
top_dramas
