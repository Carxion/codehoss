# %%
import numpy as np
import pandas as pd

scores = pd.read_csv("/data/grades.csv")[["maths", "science", "english"]].to_numpy()
scores[:3]

# %%
subject_means = np.round(scores.mean(axis=0), 1)
best_total = scores.sum(axis=1).max()
above_90 = (scores > 90).sum()
subject_means, best_total, above_90
