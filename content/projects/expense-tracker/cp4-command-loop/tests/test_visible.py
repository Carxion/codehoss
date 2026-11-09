import builtins


def run_cli(monkeypatch, capsys, path, commands):
    from main import main

    feed = iter(commands)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(feed))
    main(str(path))
    return capsys.readouterr().out.splitlines()


def test_add_and_list(monkeypatch, capsys, tmp_path):
    out = run_cli(
        monkeypatch, capsys, tmp_path / "e.json", ["add 12.50 food Lunch with Sam", "list", "quit"]
    )
    assert out == ["Added.", "Lunch with Sam: $12.50 (food)"], out
