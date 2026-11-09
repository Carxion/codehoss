def test_accuracy():
    from main import split_digits, train_model

    X_train, X_test, y_train, y_test = split_digits()
    model = train_model(X_train, y_train)
    assert model.score(X_test, y_test) >= 0.95
