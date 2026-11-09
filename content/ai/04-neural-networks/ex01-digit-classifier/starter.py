# %%
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

digits = load_digits()
X_train, X_test, y_train, y_test = train_test_split(
    digits.data / 16, digits.target, test_size=0.25, random_state=0
)

# %%
model = None  # TODO
accuracy = 0  # TODO
accuracy
