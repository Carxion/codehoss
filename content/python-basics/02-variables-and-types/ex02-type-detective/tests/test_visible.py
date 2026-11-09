def test_name_is_text(run_program):
    name = run_program().vars.get("name")
    assert name == "Ada", f"name should be the text 'Ada', got {name!r}"
