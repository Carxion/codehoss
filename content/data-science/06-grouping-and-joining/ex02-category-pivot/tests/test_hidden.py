import pandas as pd

SALES = pd.read_csv("/data/sales.csv")
SALES["revenue"] = SALES["units"] * SALES["unit_price"]
FULL = SALES.merge(pd.read_csv("/data/products.csv"), on="product")
EXPECTED = FULL.pivot_table(
    index="region", columns="category", values="revenue", aggfunc="sum"
).round(2)


def test_values(run_program):
    pivot = run_program().vars.get("pivot")
    pd.testing.assert_frame_equal(
        pivot.sort_index().sort_index(axis=1),
        EXPECTED.sort_index().sort_index(axis=1),
        check_names=False,
    )


def test_top(run_program):
    assert run_program().vars.get("top_category") == EXPECTED.sum().idxmax()
