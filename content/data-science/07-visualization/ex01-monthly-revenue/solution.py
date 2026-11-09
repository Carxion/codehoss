# %%
import matplotlib.pyplot as plt
import pandas as pd

sales = pd.read_csv("/data/sales.csv")
sales["revenue"] = sales["units"] * sales["unit_price"]

# %%
sales["month"] = pd.to_datetime(sales["date"]).dt.month
monthly = sales.groupby("month")["revenue"].sum()

# %%
plt.plot(monthly.index, monthly.values, marker="o")
plt.title("Monthly revenue")
plt.xlabel("Month")
plt.ylabel("Revenue")
