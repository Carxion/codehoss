# %%
import pandas as pd

df = pd.read_csv("/data/grades.csv")
df.head()

# %%
maths_avg = round(df["maths"].mean(), 1)
maths_avg

# %%
passed = (df["maths"] >= 60).sum()
passed
