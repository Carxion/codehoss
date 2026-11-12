import matplotlib.pyplot as plt
from hoss_checks import first_axes


def test_three_lines():
    from main import load_weather, monthly_summary, plot_temperatures

    plt.close("all")
    plot_temperatures(monthly_summary(load_weather("/data/weather.csv")))
    assert first_axes()["lines"] == 3, "Draw one line per city"
