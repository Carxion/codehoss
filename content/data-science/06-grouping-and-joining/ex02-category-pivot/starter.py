# %%
import pandas as pd

sales = pd.read_csv("/data/sales.csv")
products = pd.read_csv("/data/products.csv")
sales["revenue"] = sales["units"] * sales["unit_price"]

# %%
pivot = None  # TODO
top_category = ""  # TODO
pivot
