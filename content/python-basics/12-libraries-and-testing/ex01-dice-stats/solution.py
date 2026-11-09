import random
import statistics


def roll_dice(count, rng):
    return [rng.randint(1, 6) for _ in range(count)]


def summarize(rolls):
    return {"min": min(rolls), "max": max(rolls), "mean": round(statistics.mean(rolls), 2)}


if __name__ == "__main__":
    rolls = roll_dice(10, random.Random())
    print(rolls, summarize(rolls))
