"""Generate the Data Science module's datasets (synthetic, deterministic, license-free).

    uv run python scripts/make_datasets.py

Writes content/data-science/datasets/ and content/projects/datasets/ (the Projects
module gets its own copies of what it uses, plus a weather dataset). Standard library
only. Each dataset is shaped to teach something: the survey is messy on purpose, the
A/B test has a real but modest effect, the customers fall into three clusters, and so
on. Change the generators and
re-run; exercise tests compute expectations from the files, so they stay valid as long
as column names don't change.
"""

import csv
import math
import random
import shutil
import sqlite3
from datetime import date, timedelta
from pathlib import Path

CONTENT = Path(__file__).resolve().parent.parent / "content"
OUT = CONTENT / "data-science" / "datasets"
PROJECTS = CONTENT / "projects" / "datasets"


def write_csv(name, header, rows, folder=OUT):
    with (folder / name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def grades(rng):
    names = [
        "Ada",
        "Alan",
        "Grace",
        "Linus",
        "Margaret",
        "Dennis",
        "Barbara",
        "Ken",
        "Radia",
        "Tim",
        "Frances",
        "Guido",
        "Katherine",
        "John",
        "Hedy",
        "Claude",
        "Annie",
        "Edsger",
        "Joan",
        "Niklaus",
        "Shafi",
        "Donald",
        "Lynn",
        "Bjarne",
        "Sophie",
        "James",
        "Mary",
        "Brian",
        "Karen",
        "Vint",
    ]
    rows = []
    for name in names:
        base = rng.gauss(72, 10)
        rows.append([name] + [max(20, min(100, round(base + rng.gauss(0, 8)))) for _ in range(3)])
    write_csv("grades.csv", ["student", "maths", "science", "english"], rows)


def movies(rng):
    first = ["The", "A", "Last", "Silent", "Golden", "Hidden", "Broken", "Midnight", "Wild", "Lost"]
    second = [
        "River",
        "Star",
        "Garden",
        "City",
        "Promise",
        "Echo",
        "Harbor",
        "Machine",
        "Storm",
        "Letter",
        "Forest",
        "Signal",
    ]
    genres = {
        "Drama": 7.0,
        "Comedy": 6.3,
        "Action": 6.1,
        "Sci-Fi": 6.6,
        "Horror": 5.6,
        "Animation": 7.1,
    }
    rows, seen = [], set()
    while len(rows) < 120:
        title = f"{rng.choice(first)} {rng.choice(second)}"
        if title in seen:
            title += f" {rng.choice(['II', 'Returns', 'Rising'])}"
        if title in seen:
            continue
        seen.add(title)
        genre = rng.choice(list(genres))
        year = rng.randint(1985, 2025)
        rating = round(max(2.0, min(9.6, rng.gauss(genres[genre], 0.9))), 1)
        votes = int(rng.lognormvariate(10, 1.1))
        runtime = int(rng.gauss(118 if genre != "Animation" else 95, 15))
        gross = round(max(0.1, rng.lognormvariate(3.3, 1.2) * (rating / 6.5)), 1)
        rows.append([title, year, genre, rating, votes, runtime, gross])
    write_csv(
        "movies.csv",
        ["title", "year", "genre", "rating", "votes", "runtime", "gross_millions"],
        rows,
    )


def survey(rng):
    cities = ["Denver", "Boulder", "Austin", "Seattle"]
    messy = {
        "Denver": ["denver", " Denver", "DENVER "],
        "Austin": ["austin", "Austin "],
        "Seattle": ["seattle"],
        "Boulder": ["boulder "],
    }
    rows = []
    for i in range(1, 61):
        city = rng.choice(cities)
        if rng.random() < 0.35:
            city = rng.choice(messy[city])
        age = str(rng.randint(18, 70))
        if rng.random() < 0.1:
            age = rng.choice(["", "unknown"])
        satisfaction = str(rng.randint(1, 5)) if rng.random() > 0.12 else ""
        rows.append([i, age, city, satisfaction])
    rows += [rows[4], rows[17], rows[30]]  # duplicated submissions
    write_csv("survey_messy.csv", ["respondent", "age", "city", "satisfaction"], rows)


def sales(rng):
    products = {
        "Notebook": ("Stationery", 3.5),
        "Pen": ("Stationery", 1.2),
        "Backpack": ("Bags", 39.0),
        "Tote": ("Bags", 18.0),
        "Lamp": ("Home", 24.0),
        "Mug": ("Home", 9.5),
    }
    regions = ["North", "South", "East", "West"]
    start = date(2025, 1, 1)
    rows = []
    for order in range(1, 501):
        product = rng.choice(list(products))
        day = start + timedelta(days=rng.randint(0, 364))
        units = rng.randint(1, 8)
        region = rng.choices(regions, weights=[4, 3, 2, 1])[0]
        rows.append([order, day.isoformat(), region, product, units, products[product][1]])
    write_csv("sales.csv", ["order_id", "date", "region", "product", "units", "unit_price"], rows)
    write_csv("products.csv", ["product", "category"], [[p, c] for p, (c, _) in products.items()])


def ab_test(rng):
    rows = []
    for user in range(1, 2001):
        group = "A" if user % 2 else "B"
        rate = 0.10 if group == "A" else 0.13
        rows.append(
            [
                user,
                group,
                int(rng.random() < rate),
                round(rng.gauss(52 if group == "A" else 55, 12), 1),
            ]
        )
    write_csv("ab_test.csv", ["user_id", "group", "converted", "time_on_page"], rows)


def houses(rng):
    rows = []
    for _ in range(300):
        size = int(rng.gauss(1600, 450))
        bedrooms = max(1, min(6, round(size / 550 + rng.gauss(0, 0.6))))
        age = rng.randint(0, 80)
        distance = round(rng.uniform(1, 30), 1)
        price = 50_000 + 180 * size + 9_000 * bedrooms - 900 * age - 2_500 * distance
        rows.append([size, bedrooms, age, distance, int(price + rng.gauss(0, 25_000))])
    write_csv("houses.csv", ["size_sqft", "bedrooms", "age_years", "distance_km", "price"], rows)


def messages(rng):
    spam = [
        "WIN a FREE {prize} now",
        "Claim your {prize} prize today",
        "URGENT: you won {prize}",
        "Free {prize}! Click to claim",
        "Cheap {prize}, limited offer, act now",
    ]
    ham = [
        "Are we still on for {thing} tonight?",
        "Can you send me the {thing} notes",
        "Running late, see you at {thing}",
        "Thanks for the {thing} yesterday",
        "Did you finish the {thing} report",
    ]
    prizes = ["iPhone", "cruise", "gift card", "cash", "laptop", "vacation"]
    things = ["dinner", "meeting", "project", "class", "game", "lunch"]
    rows = []
    for _ in range(240):
        if rng.random() < 0.4:
            rows.append([rng.choice(spam).format(prize=rng.choice(prizes)), "spam"])
        else:
            rows.append([rng.choice(ham).format(thing=rng.choice(things)), "ham"])
    write_csv("messages.csv", ["text", "label"], rows)


def customers(rng):
    # Three clearly separated segments (60 each), so KMeans can find them once scaled.
    centres = [(400, 2, 25), (1800, 8, 45), (5200, 4, 160)]  # spend, visits, basket
    rows = []
    for i in range(1, 181):
        spend, visits, basket = centres[i % 3]
        rows.append(
            [
                i,
                round(rng.gauss(spend, spend * 0.08), 2),
                max(1, round(rng.gauss(visits, 0.5))),
                round(rng.gauss(basket, basket * 0.08), 2),
            ]
        )
    write_csv(
        "customers.csv", ["customer_id", "annual_spend", "visits_per_month", "avg_basket"], rows
    )


def store_db(rng):
    path = OUT / "store.db"
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT, joined TEXT);
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER,
                             quantity INTEGER, ordered TEXT);
        """
    )
    names = [
        "Ada",
        "Alan",
        "Grace",
        "Linus",
        "Margaret",
        "Dennis",
        "Barbara",
        "Ken",
        "Radia",
        "Tim",
        "Frances",
        "Guido",
    ]
    cities = ["Denver", "Boulder", "Austin", "Seattle"]
    for i, name in enumerate(names, 1):
        joined = date(2023, 1, 1) + timedelta(days=rng.randint(0, 700))
        db.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?)",
            (i, name, rng.choice(cities), joined.isoformat()),
        )
    catalog = [
        ("Notebook", "Stationery", 3.5),
        ("Pen", "Stationery", 1.2),
        ("Backpack", "Bags", 39.0),
        ("Lamp", "Home", 24.0),
        ("Mug", "Home", 9.5),
    ]
    for i, (name, category, price) in enumerate(catalog, 1):
        db.execute("INSERT INTO products VALUES (?, ?, ?, ?)", (i, name, category, price))
    for i in range(1, 151):
        ordered = date(2025, 1, 1) + timedelta(days=rng.randint(0, 300))
        db.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            (
                i,
                rng.randint(1, len(names)),
                rng.randint(1, len(catalog)),
                rng.randint(1, 5),
                ordered.isoformat(),
            ),
        )
    db.commit()
    db.close()
    print("store.db: customers, products, orders")


def weather(rng):
    """Daily weather for three cities in 2025, with a few gaps and a duplicate."""
    climates = {  # (mean temp °C, seasonal swing, rainy-month peak, rain scale)
        "Denver": (10.5, 12.0, 5, 1.2),
        "Seattle": (11.5, 7.0, 12, 3.0),
        "Austin": (21.0, 8.5, 5, 2.2),
    }
    rows = []
    for city, (mean, swing, wet_month, rain) in climates.items():
        for day in range(365):
            when = date(2025, 1, 1) + timedelta(days=day)
            seasonal = mean - swing * math.cos(2 * math.pi * (day - 15) / 365)
            high = round(seasonal + 6 + rng.gauss(0, 2.5), 1)
            low = round(seasonal - 6 + rng.gauss(0, 2.5), 1)
            wetness = 1 + math.cos(2 * math.pi * (when.month - wet_month) / 12)
            precip = (
                round(max(0.0, rng.gauss(rain * wetness, 3.0)), 1) if rng.random() < 0.35 else 0.0
            )
            wind = round(abs(rng.gauss(14, 6)), 1)
            row = [when.isoformat(), city, high, low, precip, wind]
            if rng.random() < 0.01:
                row[rng.choice([2, 3])] = ""  # a missing reading
            rows.append(row)
    rows.insert(100, list(rows[99]))  # a duplicated row
    write_csv(
        "weather.csv",
        ["date", "city", "temp_max_c", "temp_min_c", "precip_mm", "wind_kph"],
        rows,
        folder=PROJECTS,
    )


def share_with_projects():
    for name in ("houses.csv", "movies.csv"):
        shutil.copy(OUT / name, PROJECTS / name)
    handbook = CONTENT / "ai" / "datasets" / "handbook"
    if handbook.exists():
        shutil.copytree(handbook, PROJECTS / "handbook", dirs_exist_ok=True)
    print("projects: copied houses.csv, movies.csv, handbook/")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PROJECTS.mkdir(parents=True, exist_ok=True)
    for i, generate in enumerate(
        # Append new generators at the end so existing datasets keep their seeds.
        [grades, movies, survey, sales, ab_test, houses, messages, customers, store_db, weather]
    ):
        generate(random.Random(1000 + i))
    share_with_projects()


if __name__ == "__main__":
    main()
