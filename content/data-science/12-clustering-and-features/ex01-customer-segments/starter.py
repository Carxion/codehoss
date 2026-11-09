# %%
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("/data/customers.csv")
FEATURES = ["annual_spend", "visits_per_month", "avg_basket"]

# %%
# TODO: scale, cluster, and add df["segment"]
segment_sizes = []  # TODO
segment_sizes
