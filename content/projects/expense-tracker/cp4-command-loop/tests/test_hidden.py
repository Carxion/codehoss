import builtins


def test_cp1_format():
    from main import add_expense, format_expense

    expenses = []
    add_expense(expenses, "Bus pass", 40, "Transport")
    add_expense(expenses, "Coffee", 3.456, "food")
    assert format_expense(expenses[0]) == "Bus pass: $40.00 (transport)"
    assert expenses[1]["amount"] == 3.46


def test_cp2_by_category():
    from main import add_expense, totals_by_category

    expenses = []
    for description, amount, category in [
        ("a", 5, "rent"),
        ("b", 2.25, "food"),
        ("c", 1.5, "food"),
    ]:
        add_expense(expenses, description, amount, category)
    got = totals_by_category(expenses)
    assert got == {"food": 3.75, "rent": 5.0}, got
    assert list(got) == ["food", "rent"], "Categories should be in alphabetical order"


def test_cp3_missing_file(tmp_path):
    from main import load

    assert load(tmp_path / "nope.json") == []


def run_cli(monkeypatch, capsys, path, commands):
    from main import main

    feed = iter(commands)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(feed))
    main(str(path))
    return capsys.readouterr().out.splitlines()


def test_cp4_report_and_persistence(monkeypatch, capsys, tmp_path):
    path = tmp_path / "e.json"
    run_cli(monkeypatch, capsys, path, ["add 5 rent Deposit", "add 2.5 food Snack", "quit"])
    out = run_cli(monkeypatch, capsys, path, ["report", "list", "dance", "quit"])
    assert out == [
        "food: $2.50",
        "rent: $5.00",
        "Total: $7.50",
        "Deposit: $5.00 (rent)",
        "Snack: $2.50 (food)",
        "Commands: add, list, report, quit",
    ], out


def test_cp4_empty(monkeypatch, capsys, tmp_path):
    assert run_cli(monkeypatch, capsys, tmp_path / "e.json", ["list", "quit"]) == [
        "No expenses yet."
    ]
