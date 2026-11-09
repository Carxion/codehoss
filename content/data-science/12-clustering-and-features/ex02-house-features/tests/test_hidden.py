import pandas as pd
from dojo_checks import assert_close

H = pd.read_csv("/data/houses.csv")
H["price_per_sqft"] = (H["price"] / H["size_sqft"]).round(2)
H["is_new"] = H["age_years"] < 10


def test_values(run_program):
    v = run_program().vars
    assert (v["houses"]["is_new"] == H["is_new"]).all(), "is_new should be age_years < 10"
    assert_close(
        v.get("ppsf_new"), round(H[H["is_new"]]["price_per_sqft"].mean(), 2), name="ppsf_new"
    )
    assert_close(
        v.get("ppsf_old"), round(H[~H["is_new"]]["price_per_sqft"].mean(), 2), name="ppsf_old"
    )
