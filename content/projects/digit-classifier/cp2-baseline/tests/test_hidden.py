import numpy as np


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
