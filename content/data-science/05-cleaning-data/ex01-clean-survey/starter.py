# %%
import pandas as pd

raw = pd.read_csv("/data/survey_messy.csv")


def clean_survey(raw):
    df = raw.copy()
    # TODO: drop duplicates, tidy city, make age and satisfaction numbers
    return df


# %%
clean = clean_survey(raw)
clean["city"].value_counts()
