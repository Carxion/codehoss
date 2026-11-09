def test_longer():
    from main import evaluate_rpn

    assert evaluate_rpn("5 1 2 + 4 * + 3 -".split()) == 14
    assert evaluate_rpn(["4", "13", "5", "/", "+"]) == 6
    assert evaluate_rpn(["7", "-2", "/"]) == -3, "Round towards zero"
    assert evaluate_rpn(["42"]) == 42
