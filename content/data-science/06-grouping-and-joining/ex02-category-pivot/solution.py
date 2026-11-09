# %%
import pandas as pd

sales = pd.read_csv("/data/sales.csv")
products = pd.read_csv("/data/products.csv")
sales["revenue"] = sales["units"] * sales["unit_price"]

# %%
full = sales.merge(products, on="product")
pivot = full.pivot_table(index="region", columns="category", values="revenue", aggfunc="sum").round(
    2
)
top_category = pivot.sum().idxmax()
pivot
