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


# %%
def evaluate(df, features):
    train, test = train_test_split(df, test_size=0.2, random_state=42)
    baseline = [train["price"].mean()] * len(test)
    model = LinearRegression().fit(train[features], train["price"])
    return {
        "baseline_mae": mean_absolute_error(test["price"], baseline),
        "model_mae": mean_absolute_error(test["price"], model.predict(test[features])),
    }


# %%
evaluate(houses, FEATURES)


# %%
def add_features(df):
    """Copy of df plus is_new (age < 10 as 1/0) and size_per_bedroom."""
    raise NotImplementedError


ENGINEERED = FEATURES + ["is_new", "size_per_bedroom"]

# %%
evaluate(houses, FEATURES), evaluate(add_features(houses), ENGINEERED)
