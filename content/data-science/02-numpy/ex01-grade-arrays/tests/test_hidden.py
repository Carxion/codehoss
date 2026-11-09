import pandas as pd

SCORES = pd.read_csv("/data/grades.csv")[["maths", "science", "english"]].to_numpy()


def test_best_total(run_program):
    got = run_program().vars.get("best_total")
    assert got == SCORES.sum(axis=1).max(), f"best_total is {got}"


def test_above_90(run_program):
    got = run_program().vars.get("above_90")
    assert got == (SCORES > 90).sum(), f"above_90 is {got}"
