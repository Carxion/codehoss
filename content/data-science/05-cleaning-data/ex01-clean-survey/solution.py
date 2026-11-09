# %%
import pandas as pd

raw = pd.read_csv("/data/survey_messy.csv")


def clean_survey(raw):
    df = raw.drop_duplicates().copy()
    df["city"] = df["city"].str.strip().str.title()
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["satisfaction"] = pd.to_numeric(df["satisfaction"], errors="coerce")
    return df


# %%
clean = clean_survey(raw)
clean["city"].value_counts()
