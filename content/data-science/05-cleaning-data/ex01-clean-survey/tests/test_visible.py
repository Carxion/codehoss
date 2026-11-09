import pandas as pd


def test_no_duplicates():
    from main import clean_survey

    clean = clean_survey(pd.read_csv("/data/survey_messy.csv"))
    assert not clean.duplicated().any(), "There are still duplicate rows"
