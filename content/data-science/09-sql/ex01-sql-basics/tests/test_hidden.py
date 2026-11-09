import sqlite3

import pandas as pd
from dojo_checks import assert_frame_matches

CON = sqlite3.connect("/data/store.db")


def test_denver(run_program):
    customers = pd.read_sql("SELECT * FROM customers", CON)
    expected = customers[customers["city"] == "Denver"].sort_values("name")[["name", "joined"]]
    assert_frame_matches(run_program().vars.get("denver"), expected, name="denver")


def test_orders(run_program):
    assert run_program().vars.get("n_orders") == len(pd.read_sql("SELECT * FROM orders", CON))
