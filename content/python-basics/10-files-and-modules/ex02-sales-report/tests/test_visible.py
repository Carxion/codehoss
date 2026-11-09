SALES = "item,amount\ntea,3.50\ncake,4.25\ntea,3.50\n"


def test_total(tmp_path):
    from main import total_sales

    path = tmp_path / "sales.csv"
    path.write_text(SALES)
    assert round(total_sales(path), 2) == 11.25, f"total_sales gave {total_sales(path)}"
