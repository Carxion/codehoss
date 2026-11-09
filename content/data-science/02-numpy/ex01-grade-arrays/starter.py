# %%
import numpy as np
import pandas as pd

scores = pd.read_csv("/data/grades.csv")[["maths", "science", "english"]].to_numpy()
scores[:3]

# %%
subject_means = None  # TODO
best_total = 0  # TODO
above_90 = 0  # TODO
subject_means, best_total, above_90
