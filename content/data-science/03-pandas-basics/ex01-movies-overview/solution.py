# %%
import pandas as pd

df = pd.read_csv("/data/movies.csv")
df.head()

# %%
n_movies = len(df)
n_genres = df["genre"].nunique()
avg_rating = round(df["rating"].mean(), 2)
top_genre = df["genre"].value_counts().idxmax()
n_movies, n_genres, avg_rating, top_genre
