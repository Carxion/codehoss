import sqlite3

import pandas as pd
from dojo_checks import assert_frame_matches

CON = sqlite3.connect("/data/store.db")


def test_values(run_program):
    orders = pd.read_sql("SELECT * FROM orders", CON)
    products = pd.read_sql("SELECT id AS product_id, price FROM products", CON)
    customers = pd.read_sql("SELECT id AS customer_id, name FROM customers", CON)
    full = orders.merge(products, on="product_id").merge(customers, on="customer_id")
    full["revenue"] = full["quantity"] * full["price"]
    expected = (
        full.groupby("name", as_index=False)["revenue"]
        .sum()
        .round(2)
        .sort_values("revenue", ascending=False)
        .head(5)
    )
    assert_frame_matches(run_program().vars.get("top_customers"), expected, name="top_customers")
