# %%
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

houses = pd.read_csv("/data/houses.csv")
FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]

# %%
model = None  # TODO
mae = 0  # TODO
mae
