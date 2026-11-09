# %%
import numpy as np
from sklearn.datasets import load_digits
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier


def split_digits():
    digits = load_digits()
    # TODO: scale the pixels to 0..1 and split with test_size=0.25, random_state=0,
    #   stratify=digits.target
    return None, None, None, None


# %%
X_train, X_test, y_train, y_test = split_digits()
