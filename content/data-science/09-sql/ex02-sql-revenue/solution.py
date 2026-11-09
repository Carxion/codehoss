# %%
import sqlite3

import pandas as pd

con = sqlite3.connect("/data/store.db")

# %%
query = """
SELECT c.name, SUM(o.quantity * p.price) AS revenue
FROM orders o
JOIN products p ON p.id = o.product_id
JOIN customers c ON c.id = o.customer_id
GROUP BY c.name
ORDER BY revenue DESC
LIMIT 5
"""
top_customers = pd.read_sql(query, con).round(2)
top_customers
