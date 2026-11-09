import pandas as pd


def test_passed(run_program):
    df = pd.read_csv("/data/grades.csv")
    expected = int((df["maths"] >= 60).sum())
    passed = run_program().vars.get("passed")
    assert passed == expected, f"passed should be {expected}, but it is {passed!r}"
