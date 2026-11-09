import pandas as pd


def test_rows():
    from main import explore

    assert explore(pd.read_csv("/data/houses.csv"))["rows"] == 300
