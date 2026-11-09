def test_heading_and_table():
    from main import build_report, load_weather, monthly_summary

    html = build_report(monthly_summary(load_weather("/data/weather.csv")))
    assert "<h1>Weather report</h1>" in html
    assert "<table" in html, "Include summary.to_html(index=False)"
