import hoss_ai


def test_two_examples():
    from main import few_shot_prompt

    got = few_shot_prompt("X", [("a", "1"), ("b", "2")], "c")
    assert got == "X\n\nInput: a\nOutput: 1\n\nInput: b\nOutput: 2\n\nInput: c\nOutput:"


def test_classify():
    from main import EXAMPLES, INSTRUCTION, classify, few_shot_prompt

    hoss_ai.fake(chat=lambda messages, **kw: "  Neutral\n")

    assert classify("The box was blue.") == "neutral"
    assert hoss_ai.calls[-1]["messages"][-1]["content"] == few_shot_prompt(
        INSTRUCTION, EXAMPLES, "The box was blue."
    )
