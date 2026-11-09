import pandas as pd


def test_heading():
    from main import report

    text = report(pd.read_csv("/data/houses.csv"))
    assert text.splitlines()[0] == "# House price report"
    assert "Houses analysed: 300" in text
