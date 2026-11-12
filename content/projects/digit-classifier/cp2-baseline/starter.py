# %%
import numpy as np
from sklearn.datasets import load_digits
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier


def split_digits():
    digits = load_digits()
    return train_test_split(
        digits.data / 16, digits.target, test_size=0.25, random_state=0, stratify=digits.target
    )


# %%
X_train, X_test, y_train, y_test = split_digits()
X_train.shape, X_test.shape


# %%
def baseline_accuracy(y_train, y_test):
    guess = 0  # TODO: the most common digit in y_train
    return 0.0  # TODO: share of y_test equal to guess


# %%
baseline_accuracy(y_train, y_test)
