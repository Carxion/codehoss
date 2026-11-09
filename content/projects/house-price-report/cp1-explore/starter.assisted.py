# %%
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]
houses = pd.read_csv("/data/houses.csv")


def explore(df):
    """{"rows", "price_mean", "price_median" (whole $), "strongest_feature" (max |corr|)}."""
    raise NotImplementedError


# %%
explore(houses)
