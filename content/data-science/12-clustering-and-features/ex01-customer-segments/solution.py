# %%
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("/data/customers.csv")
FEATURES = ["annual_spend", "visits_per_month", "avg_basket"]

# %%
scaled = StandardScaler().fit_transform(df[FEATURES])
df["segment"] = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(scaled)
segment_sizes = sorted(df["segment"].value_counts().tolist())
segment_sizes

# %%
df.groupby("segment")[FEATURES].mean().round(1)
