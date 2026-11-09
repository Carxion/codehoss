# %%
import sqlite3

import pandas as pd

con = sqlite3.connect("/data/store.db")

# %%
denver = pd.read_sql("SELECT name, joined FROM customers WHERE city = 'Denver' ORDER BY name", con)
n_orders = int(pd.read_sql("SELECT COUNT(*) AS n FROM orders", con)["n"][0])
denver
