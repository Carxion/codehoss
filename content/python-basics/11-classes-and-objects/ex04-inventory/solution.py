from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
    qty: int = 0

    @property
    def value(self):
        return self.price * self.qty


class Inventory:
    def __init__(self):
        self.items = {}

    def add(self, item):
        if item.name in self.items:
            raise ValueError(f"{item.name} is already in stock")
        self.items[item.name] = item

    def restock(self, name, amount):
        self.items[name].qty += amount

    def total_value(self):
        return round(sum([item.value for item in self.items.values()]), 2)

    def low_stock(self, limit=5):
        return sorted([name for name, item in self.items.items() if item.qty < limit])
