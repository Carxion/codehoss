# %%
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

messages = pd.read_csv("/data/messages.csv")
train_text, test_text, y_train, y_test = train_test_split(
    messages["text"], messages["label"], test_size=0.25, random_state=42, stratify=messages["label"]
)

# %%
vectorizer = CountVectorizer()
X_train = vectorizer.fit_transform(train_text)
X_test = vectorizer.transform(test_text)
model = MultinomialNB().fit(X_train, y_train)
predictions = model.predict(X_test)

# %%
cm = None  # TODO
false_positives = -1  # TODO
false_negatives = -1  # TODO
cm
