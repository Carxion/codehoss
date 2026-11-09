# %%
import matplotlib.pyplot as plt
import pandas as pd


def load_weather(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.drop_duplicates().dropna(subset=["temp_max_c", "temp_min_c"])
    df["temp_mean_c"] = (df["temp_max_c"] + df["temp_min_c"]) / 2
    return df.reset_index(drop=True)


# %%
weather = load_weather("/data/weather.csv")
weather.head()


def monthly_summary(df):
    df = df.assign(month=df["date"].dt.month)
    summary = df.groupby(["city", "month"]).agg(
        avg_temp_c=("temp_mean_c", "mean"), total_precip_mm=("precip_mm", "sum")
    )
    return summary.round(1).reset_index()


# %%
summary = monthly_summary(weather)
summary.head(12)


def plot_temperatures(summary):
    for city, rows in summary.groupby("city"):
        plt.plot(rows["month"], rows["avg_temp_c"], marker="o", label=city)
    plt.title("Average temperature by month")
    plt.xlabel("Month")
    plt.ylabel("°C")
    plt.legend()


# %%
plot_temperatures(summary)


def build_report(summary):
    lines = ["<h1>Weather report</h1>"]
    for city, rows in summary.groupby("city"):
        warmest = rows.loc[rows["avg_temp_c"].idxmax(), "month"]
        wettest = rows.loc[rows["total_precip_mm"].idxmax(), "month"]
        lines.append(f"<p><b>{city}</b>: warmest month {warmest}, wettest month {wettest}</p>")
    lines.append(summary.to_html(index=False))
    return "\n".join(lines)


def save_report(html, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# %%
report = build_report(summary)
save_report(report, "weather_report.html")
print(report[:400])
