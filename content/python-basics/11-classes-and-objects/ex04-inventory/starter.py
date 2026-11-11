from dataclasses import dataclass


# TODO: make Item a dataclass with name, price, qty (default 0) and a value property
class Item:
    pass


class Inventory:
    def __init__(self):
        self.items = {}

    def add(self, item):
        # TODO: add the item; raise ValueError if the name is already used
        pass

    def restock(self, name, amount):
        # TODO
        pass

    def total_value(self):
        # TODO: the value of everything, rounded to 2 decimals
        return 0

    def low_stock(self, limit=5):
        # TODO: sorted names of items with fewer than `limit` in stock
        return []
