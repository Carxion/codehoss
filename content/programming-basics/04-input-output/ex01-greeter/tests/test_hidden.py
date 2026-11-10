def test_another_person(run_program):
    result = run_program(["Grace", "85"])
    assert result.lines[:2] == ["What is your name? Grace", "How old are you? 85"], (
        "Ask exactly: What is your name? then How old are you?"
    )
    assert result.last_line == "Hello, Grace! Next year you will be 86."
