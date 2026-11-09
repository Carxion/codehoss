from sklearn.datasets import load_digits


def test_predict_digit():
    from main import predict_digit, split_digits, train_model

    X_train, X_test, y_train, y_test = split_digits()
    model = train_model(X_train, y_train)
    digits = load_digits()
    got = predict_digit(model, list(digits.data[0]))
    assert isinstance(got, int) and got == digits.target[0]
