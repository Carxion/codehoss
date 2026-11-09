def test_clean():
    from main import load_weather

    df = load_weather("/data/weather.csv")
    assert not df.duplicated().any(), "Remove duplicate rows"
    assert df[["temp_max_c", "temp_min_c"]].notna().all().all(), (
        "Drop rows with missing temperatures"
    )
