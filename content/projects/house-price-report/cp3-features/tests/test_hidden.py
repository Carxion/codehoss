import pandas as pd
from dojo_checks import assert_close
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]


def test_cp1_facts():
    from main import explore

    df = pd.read_csv("/data/houses.csv")
    got = explore(df)
    assert got["price_mean"] == round(df["price"].mean())
    assert got["price_median"] == round(df["price"].median())
    assert got["strongest_feature"] == df[FEATURES].corrwith(df["price"]).abs().idxmax()


FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]


def expected_eval(df, features):
    train, test = train_test_split(df, test_size=0.2, random_state=42)
    model = LinearRegression().fit(train[features], train["price"])
    return {
        "baseline_mae": mean_absolute_error(test["price"], [train["price"].mean()] * len(test)),
        "model_mae": mean_absolute_error(test["price"], model.predict(test[features])),
    }


def test_cp2_numbers():
    from main import evaluate

    df = pd.read_csv("/data/houses.csv")
    got, want = evaluate(df, FEATURES), expected_eval(df, FEATURES)
    assert_close(float(got["baseline_mae"]), want["baseline_mae"], name="baseline_mae")
    assert_close(float(got["model_mae"]), want["model_mae"], name="model_mae")


def test_cp3_values_and_copy():
    from main import add_features

    original = pd.read_csv("/data/houses.csv")
    df = add_features(original)
    assert "is_new" not in original.columns, "Work on a copy"
    assert (df["is_new"] == (original["age_years"] < 10).astype(int)).all()
    assert (
        (df["size_per_bedroom"] - original["size_sqft"] / original["bedrooms"]).abs() < 1e-9
    ).all()
