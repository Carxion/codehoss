import pandas as pd


def clean():
    from main import clean_survey

    return clean_survey(pd.read_csv("/data/survey_messy.csv"))


def test_cities():
    cities = set(clean()["city"])
    assert cities == {"Austin", "Boulder", "Denver", "Seattle"}, f"cities are {cities}"


def test_numbers():
    df = clean()
    for column in ("age", "satisfaction"):
        assert pd.api.types.is_numeric_dtype(df[column]), f"{column} should be numeric"
    assert df["age"].isna().sum() > 0, "Values like 'unknown' should become missing"


def test_raw_unchanged():
    from main import clean_survey

    raw = pd.read_csv("/data/survey_messy.csv")
    clean_survey(raw)
    assert len(raw) == 63, "clean_survey should not change the DataFrame it is given"
