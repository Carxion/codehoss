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
vectorizer = None  # TODO
model = None  # TODO
predictions = None  # TODO
accuracy = 0  # TODO
accuracy
