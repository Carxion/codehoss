import pandas as pd


def test_df_is_loaded(run_program):
    df = run_program().vars.get("df")
    assert isinstance(df, pd.DataFrame), "df should be the DataFrame from pd.read_csv"


def test_columns(run_program):
    columns = run_program().vars.get("columns")
    assert columns == ["student", "maths", "science", "english"], f"columns is {columns!r}"
