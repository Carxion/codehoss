import numpy as np
from sklearn.metrics import confusion_matrix


def test_cp1_scaled_and_stratified():
    from main import split_digits

    X_train, X_test, y_train, y_test = split_digits()
    assert X_train.max() <= 1.0, "Divide the pixels by 16"
    import numpy as np

    train_share = np.bincount(y_train) / len(y_train)
    test_share = np.bincount(y_test) / len(y_test)
    assert abs(train_share - test_share).max() < 0.01, "Use stratify so digits are balanced"


def test_cp2_digits():
    from main import baseline_accuracy, split_digits

    X_train, X_test, y_train, y_test = split_digits()
    expected = (y_test == np.bincount(y_train).argmax()).mean()
    assert abs(baseline_accuracy(y_train, y_test) - expected) < 1e-9


def test_cp3_settings():
    from main import split_digits, train_model

    X_train, X_test, y_train, y_test = split_digits()
    model = train_model(X_train, y_train)
    assert model.hidden_layer_sizes == (64,) and model.random_state == 0


def test_cp4_most_confused():
    from main import most_confused, split_digits, train_model

    X_train, X_test, y_train, y_test = split_digits()
    model = train_model(X_train, y_train)
    cm = confusion_matrix(y_test, model.predict(X_test), labels=range(10))
    np.fill_diagonal(cm, 0)
    expected = tuple(int(v) for v in np.unravel_index(cm.argmax(), cm.shape))
    assert most_confused(model, X_test, y_test) == expected
