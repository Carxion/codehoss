import dataclasses

import pytest


def test_item_is_a_dataclass_with_a_value_property():
    from main import Item

    assert dataclasses.is_dataclass(Item), "Item should be a dataclass (@dataclass)"
    item = Item("mug", 6.25, 4)
    assert item.value == 25.0, f"Item('mug', 6.25, 4).value gave {item.value!r}"
    assert Item("mug", 6.25).qty == 0, "qty should default to 0"
    assert Item("a", 1.0, 2) == Item("a", 1.0, 2), "Two identical items should be equal"


def test_duplicate_names_are_refused():
    from main import Inventory, Item

    shop = Inventory()
    shop.add(Item("pen", 1.5, 10))
    with pytest.raises(ValueError):
        shop.add(Item("pen", 2.0, 1))
    assert shop.items["pen"].price == 1.5, "The original item should be kept"


def test_restock_unknown_item():
    from main import Inventory

    with pytest.raises(KeyError):
        Inventory().restock("ghost", 1)


def test_low_stock_limit_and_order():
    from main import Inventory, Item

    shop = Inventory()
    for name, qty in [("zip", 1), ("bag", 9), ("cap", 4), ("axe", 0)]:
        shop.add(Item(name, 2.0, qty))
    assert shop.low_stock() == ["axe", "cap", "zip"], f"low_stock() gave {shop.low_stock()!r}"
    assert shop.low_stock(limit=1) == ["axe"], f"low_stock(limit=1) gave {shop.low_stock(limit=1)!r}"
    assert shop.total_value() == 28.0


def test_total_value_is_rounded():
    from main import Inventory, Item

    shop = Inventory()
    shop.add(Item("a", 0.1, 3))
    assert shop.total_value() == 0.3, f"total_value() gave {shop.total_value()!r}"
