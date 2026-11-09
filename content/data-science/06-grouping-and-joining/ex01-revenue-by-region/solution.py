# %%
import pandas as pd

sales = pd.read_csv("/data/sales.csv")

# %%
sales["revenue"] = sales["units"] * sales["unit_price"]
revenue_by_region = sales.groupby("region")["revenue"].sum().round(2).sort_values(ascending=False)
best_region = revenue_by_region.index[0]
revenue_by_region
