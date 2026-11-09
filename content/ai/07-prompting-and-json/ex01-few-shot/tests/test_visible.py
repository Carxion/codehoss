def test_prompt():
    from main import few_shot_prompt

    got = few_shot_prompt("Do it.", [("a", "1")], "b")
    assert got == "Do it.\n\nInput: a\nOutput: 1\n\nInput: b\nOutput:", f"Got:\n{got}"
