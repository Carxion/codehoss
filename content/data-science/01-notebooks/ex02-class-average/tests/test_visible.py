import pandas as pd
from hoss_checks import assert_close


def test_average(run_program):
    expected = round(pd.read_csv("/data/grades.csv")["maths"].mean(), 1)
    assert_close(run_program().vars.get("maths_avg"), expected, name="maths_avg")
