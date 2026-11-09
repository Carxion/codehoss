# %%
import pandas as pd

houses = pd.read_csv("/data/houses.csv")

# %%
houses["price_per_sqft"] = (houses["price"] / houses["size_sqft"]).round(2)
houses["is_new"] = houses["age_years"] < 10

ppsf_new = round(houses[houses["is_new"]]["price_per_sqft"].mean(), 2)
ppsf_old = round(houses[~houses["is_new"]]["price_per_sqft"].mean(), 2)
ppsf_new, ppsf_old
