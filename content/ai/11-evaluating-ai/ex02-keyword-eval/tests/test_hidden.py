import hoss_ai


def test_partial():
    from main import keyword_score

    assert keyword_score("thirty days", ["30", "days"]) == 0.5


def test_run_eval():
    answers = {"q1": "It is 30 days", "q2": "two years"}
    from main import run_eval

    hoss_ai.fake(chat=lambda messages, **kw: answers[messages[-1]["content"]])

    cases = [
        {"question": "q1", "keywords": ["30", "days"]},
        {"question": "q2", "keywords": ["lifetime"]},
    ]
    assert run_eval(cases) == 0.5
    assert len(hoss_ai.calls) == 2
    assert run_eval([]) == 0.0
