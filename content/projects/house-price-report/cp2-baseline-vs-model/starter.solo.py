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
        "rows": len(df),
        "price_mean": round(df["price"].mean()),
        "price_median": round(df["price"].median()),
        "strongest_feature": correlations.abs().idxmax(),
    }


# %%
explore(houses)


# Checkpoint 2: Baseline vs model. Build it your way.
