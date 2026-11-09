import pytest


def test_withdraw():
    from main import BankAccount

    account = BankAccount("Alan")
    account.deposit(10)
    account.withdraw(2.5)
    assert account.statement() == "Alan has $7.50"


def test_overdraw_is_refused():
    from main import BankAccount

    account = BankAccount("Grace", 5)
    with pytest.raises(ValueError):
        account.withdraw(6)
    assert account.statement() == "Grace has $5.00", "The balance should not change"


def test_bad_deposit():
    from main import BankAccount

    with pytest.raises(ValueError):
        BankAccount("Ada").deposit(0)
