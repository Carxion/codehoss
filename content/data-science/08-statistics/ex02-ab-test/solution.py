# %%
import pandas as pd
from scipy import stats

df = pd.read_csv("/data/ab_test.csv")
df.groupby("group")["converted"].agg(["count", "mean"])

# %%
converted_a = df[df["group"] == "A"]["converted"]
converted_b = df[df["group"] == "B"]["converted"]
rate_a = round(converted_a.mean(), 4)
rate_b = round(converted_b.mean(), 4)
lift = round(rate_b - rate_a, 4)

# %%
p_value = stats.ttest_ind(converted_b, converted_a).pvalue
significant = p_value < 0.05
lift, p_value, significant
