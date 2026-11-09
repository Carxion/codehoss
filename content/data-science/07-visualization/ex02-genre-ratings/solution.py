# %%
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("/data/movies.csv")

# %%
avg_by_genre = df.groupby("genre")["rating"].mean().sort_values(ascending=False)

# %%
plt.bar(avg_by_genre.index, avg_by_genre.values)
plt.title("Average rating by genre")
plt.ylabel("Average rating")
