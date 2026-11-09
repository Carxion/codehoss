# %%
import pandas as pd

df = pd.read_csv("/data/movies.csv")

# %%
hits = df[(df["rating"] >= 7) & (df["gross_millions"] >= 50)]
hit_rate = round(len(hits) / len(df), 3)
hits_by_genre = hits["genre"].value_counts().to_dict()
hit_rate, hits_by_genre
