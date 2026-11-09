# %%
import pandas as pd


def clean_survey(raw):
    df = raw.drop_duplicates().copy()
    df["city"] = df["city"].str.strip().str.title()
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["satisfaction"] = pd.to_numeric(df["satisfaction"], errors="coerce")
    return df


clean = clean_survey(pd.read_csv("/data/survey_messy.csv"))

# %%
median_age = clean["age"].median()
clean["age"] = clean["age"].fillna(median_age)

satisfaction_by_city = clean.groupby("city")["satisfaction"].mean().round(2).to_dict()
median_age, satisfaction_by_city
