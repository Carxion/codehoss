import pandas as pd

DF = pd.read_csv("/data/movies.csv")


def test_n_movies(run_program):
    assert run_program().vars.get("n_movies") == len(DF)
