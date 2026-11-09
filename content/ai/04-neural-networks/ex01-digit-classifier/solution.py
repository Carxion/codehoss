# %%
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

digits = load_digits()
X_train, X_test, y_train, y_test = train_test_split(
    digits.data / 16, digits.target, test_size=0.25, random_state=0
)

# %%
model = MLPClassifier(hidden_layer_sizes=(64,), max_iter=500, random_state=0).fit(X_train, y_train)
accuracy = model.score(X_test, y_test)
accuracy
