import numpy as np
import pandas as pd

SCORES = pd.read_csv("/data/grades.csv")[["maths", "science", "english"]].to_numpy()


def test_subject_means(run_program):
    got = run_program().vars.get("subject_means")
    assert got is not None and np.allclose(got, np.round(SCORES.mean(axis=0), 1)), (
        f"subject_means is {got}"
    )
