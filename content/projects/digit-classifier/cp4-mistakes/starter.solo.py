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
    guess = np.bincount(y_train).argmax()
    return float((y_test == guess).mean())


# %%
baseline_accuracy(y_train, y_test)


# %%
def train_model(X_train, y_train):
    return MLPClassifier(hidden_layer_sizes=(64,), max_iter=500, random_state=0).fit(X_train, y_train)


# %%
model = train_model(X_train, y_train)
model.score(X_test, y_test), baseline_accuracy(y_train, y_test)


# Checkpoint 4: Learn from mistakes. Build it your way.
