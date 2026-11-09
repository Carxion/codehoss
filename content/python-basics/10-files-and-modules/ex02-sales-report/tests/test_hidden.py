import pytest

SALES = "item,amount\ntea,3.50\ncake,4.25\ntea,3.50\n"
MORE = "item,amount\npie,2.00\ncake,9.00\npie,2.00\npie,2.00\n"


@pytest.mark.parametrize(("data", "total", "best"), [(SALES, 11.25, "tea"), (MORE, 15.0, "cake")])
def test_report(tmp_path, data, total, best):
    from main import best_seller, total_sales

    path = tmp_path / "sales.csv"
    path.write_text(data)
    assert round(total_sales(path), 2) == total
    assert best_seller(path) == best, f"best_seller gave {best_seller(path)!r}"
