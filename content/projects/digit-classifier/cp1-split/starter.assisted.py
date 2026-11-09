# %%
import numpy as np
from sklearn.datasets import load_digits
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier


def split_digits():
    """X_train, X_test, y_train, y_test: pixels / 16, test_size 0.25, random_state 0, stratified."""
    raise NotImplementedError


# %%
X_train, X_test, y_train, y_test = split_digits()
