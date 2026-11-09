class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Deposits must be more than 0")
        self.balance += amount

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("Not enough money")
        self.balance -= amount

    def statement(self):
        return f"{self.owner} has ${self.balance:.2f}"
