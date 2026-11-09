from sklearn.metrics import accuracy_score


def test_consistent(run_program):
    v = run_program().vars
    assert len(v["predictions"]) == len(v["y_test"]), "Predict every test message"
    assert abs(v["accuracy"] - accuracy_score(v["y_test"], v["predictions"])) < 1e-9
    assert hasattr(v["vectorizer"], "vocabulary_"), "Fit the vectorizer on train_text"
