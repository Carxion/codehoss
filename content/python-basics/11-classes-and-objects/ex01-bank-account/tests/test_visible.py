def test_deposit_and_statement():
    from main import BankAccount

    account = BankAccount("Ada", 20)
    account.deposit(30)
    assert account.statement() == "Ada has $50.00", f"statement() gave {account.statement()!r}"
