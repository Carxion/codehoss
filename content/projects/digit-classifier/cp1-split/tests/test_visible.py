def test_sizes():
    from main import split_digits

    X_train, X_test, y_train, y_test = split_digits()
    assert len(X_test) == 450 and len(X_train) == 1347, (len(X_train), len(X_test))
