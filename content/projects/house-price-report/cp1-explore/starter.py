# %%
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]
houses = pd.read_csv("/data/houses.csv")


def explore(df):
    correlations = df[FEATURES].corrwith(df["price"])
    return {
        "rows": 0,  # TODO
        "price_mean": 0,  # TODO: whole dollars
        "price_median": 0,  # TODO: whole dollars
        "strongest_feature": "",  # TODO: largest absolute correlation
    }


# %%
explore(houses)
