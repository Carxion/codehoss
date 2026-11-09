import pandas as pd
from dojo_checks import assert_close
from scipy import stats

DF = pd.read_csv("/data/ab_test.csv")
A = DF[DF["group"] == "A"]["converted"]
B = DF[DF["group"] == "B"]["converted"]


def test_lift(run_program):
    expected = round(round(B.mean(), 4) - round(A.mean(), 4), 4)
    assert_close(run_program().vars.get("lift"), expected, name="lift")


def test_p_value(run_program):
    v = run_program().vars
    expected = stats.ttest_ind(B, A).pvalue
    assert_close(float(v.get("p_value")), expected, name="p_value", tol=1e-9)
    assert bool(v.get("significant")) == (expected < 0.05), "significant should be p_value < 0.05"
