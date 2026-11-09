import pandas as pd
from dojo_checks import assert_close

DF = pd.read_csv("/data/movies.csv")


def test_n_genres(run_program):
    assert run_program().vars.get("n_genres") == DF["genre"].nunique()


def test_avg_rating(run_program):
    assert_close(
        run_program().vars.get("avg_rating"), round(DF["rating"].mean(), 2), name="avg_rating"
    )


def test_top_genre(run_program):
    got = run_program().vars.get("top_genre")
    assert got == DF["genre"].value_counts().idxmax(), f"top_genre is {got!r}"
