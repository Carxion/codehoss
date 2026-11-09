import pandas as pd


def expected_weather():
    df = pd.read_csv("/data/weather.csv", parse_dates=["date"]).drop_duplicates()
    df = df.dropna(subset=["temp_max_c", "temp_min_c"])
    df["temp_mean_c"] = (df["temp_max_c"] + df["temp_min_c"]) / 2
    return df.reset_index(drop=True)


def test_cp1_columns_and_rows():
    from main import load_weather

    df = load_weather("/data/weather.csv")
    expected = expected_weather()
    assert len(df) == len(expected), f"Expected {len(expected)} rows, got {len(df)}"
    assert pd.api.types.is_datetime64_any_dtype(df["date"]), "Parse date as dates"
    assert (df["temp_mean_c"] - expected["temp_mean_c"]).abs().max() < 1e-9
    assert list(df.index) == list(range(len(df))), "Reset the index"
