def test_four_items(run_program):
    result = run_program(["bread", "jam", "tea", "rice", "done"])
    assert result.vars.get("items") == ["bread", "jam", "tea", "rice"], (
        "items should hold every answer except done"
    )
    assert result.lines[-5:] == ["You need 4 items:", "- bread", "- jam", "- tea", "- rice"]


def test_nothing(run_program):
    assert run_program(["done"]).last_line == "You need 0 items:"
