# %%
import matplotlib.pyplot as plt
import pandas as pd

sales = pd.read_csv("/data/sales.csv")
sales["revenue"] = sales["units"] * sales["unit_price"]

# %%
monthly = None  # TODO

# %%
# TODO: draw the line chart with a title and axis labels
