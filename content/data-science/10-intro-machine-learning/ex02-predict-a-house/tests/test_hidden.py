import pandas as pd
from hoss_checks import assert_close
from sklearn.linear_model import LinearRegression

HOUSES = pd.read_csv("/data/houses.csv")
FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]


def test_exact(run_program):
    model = LinearRegression().fit(HOUSES[FEATURES], HOUSES["price"])
    new = pd.DataFrame([{"size_sqft": 1800, "bedrooms": 3, "age_years": 10, "distance_km": 5}])
    assert_close(
        float(run_program().vars.get("predicted")), model.predict(new)[0], name="predicted"
    )
