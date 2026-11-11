def test_example():
    from main import Inventory, Item

    shop = Inventory()
    shop.add(Item("pen", 1.5, 10))
    shop.add(Item("ink", 4.0))
    shop.restock("ink", 3)
    assert shop.total_value() == 27.0, f"total_value() gave {shop.total_value()!r}"
    assert shop.low_stock() == ["ink"], f"low_stock() gave {shop.low_stock()!r}"
