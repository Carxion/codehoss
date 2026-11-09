# %%
import pandas as pd

df = pd.read_csv("/data/grades.csv")

# %%
students = len(df)
columns = list(df.columns)
students, columns
