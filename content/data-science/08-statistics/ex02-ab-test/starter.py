# %%
import pandas as pd
from scipy import stats

df = pd.read_csv("/data/ab_test.csv")
df.groupby("group")["converted"].agg(["count", "mean"])

# %%
rate_a = 0  # TODO
rate_b = 0  # TODO
lift = 0  # TODO

# %%
p_value = 1.0  # TODO
significant = False  # TODO
lift, p_value, significant
