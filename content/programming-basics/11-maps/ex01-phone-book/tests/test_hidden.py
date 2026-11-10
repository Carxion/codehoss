def test_others(run_program):
    assert run_program(["Alan"]).last_line == "Alan: 555-0123"
    assert run_program(["Bob"]).last_line == "Sorry, no number for Bob"
    assert run_program(["ada"]).last_line == "Sorry, no number for ada", (
        "Keys are exact: ada isn't Ada"
    )
