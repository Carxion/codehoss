import pandas as pd


def test_students(run_program):
    students = run_program().vars.get("students")
    expected = len(pd.read_csv("/data/grades.csv"))
    assert students == expected, f"students should be {expected}, but it is {students!r}"
