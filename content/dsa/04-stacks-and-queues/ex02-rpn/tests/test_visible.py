def test_simple():
    from main import evaluate_rpn

    assert evaluate_rpn(["3", "4", "+"]) == 7
