import matplotlib.pyplot as plt
import pandas as pd
from dojo_checks import assert_frame_matches, first_axes


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


def test_cp2_values():
    from main import load_weather, monthly_summary

    df = load_weather("/data/weather.csv")
    expected = (
        df.assign(month=df["date"].dt.month)
        .groupby(["city", "month"])
        .agg(avg_temp_c=("temp_mean_c", "mean"), total_precip_mm=("precip_mm", "sum"))
        .round(1)
        .reset_index()
    )
    assert_frame_matches(monthly_summary(df), expected, name="summary")


def test_cp3_labels():
    from main import load_weather, monthly_summary, plot_temperatures

    plt.close("all")
    plot_temperatures(monthly_summary(load_weather("/data/weather.csv")))
    ax = first_axes()
    assert ax["title"] == "Average temperature by month", ax["title"]
    assert (ax["xlabel"], ax["ylabel"]) == ("Month", "°C")
    assert sorted(ax["legend"]) == ["Austin", "Denver", "Seattle"], ax["legend"]
