# %%
import pandas as pd
from sklearn.linear_model import LinearRegression

houses = pd.read_csv("/data/houses.csv")
FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]
new_house = pd.DataFrame([{"size_sqft": 1800, "bedrooms": 3, "age_years": 10, "distance_km": 5}])

# %%
predicted = 0  # TODO
predicted
