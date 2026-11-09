def test_list_is_updated(run_program):
    shopping = run_program().vars.get("shopping")
    assert shopping == ["apples", "milk", "bread"], f"shopping is {shopping}"
