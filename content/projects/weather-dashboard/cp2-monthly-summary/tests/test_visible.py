def test_shape():
    from main import load_weather, monthly_summary

    summary = monthly_summary(load_weather("/data/weather.csv"))
    assert list(summary.columns) == ["city", "month", "avg_temp_c", "total_precip_mm"], list(
        summary.columns
    )
    assert len(summary) == 36, "3 cities x 12 months"
