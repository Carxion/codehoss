import pandas as pd
from dojo_checks import assert_close
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

HOUSES = pd.read_csv("/data/houses.csv")
FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]


def test_mae(run_program):
    X_train, X_test, y_train, y_test = train_test_split(
        HOUSES[FEATURES], HOUSES["price"], test_size=0.2, random_state=42
    )
    expected = mean_absolute_error(y_test, LinearRegression().fit(X_train, y_train).predict(X_test))
    assert_close(float(run_program().vars.get("mae")), expected, name="mae", tol=1e-6)
