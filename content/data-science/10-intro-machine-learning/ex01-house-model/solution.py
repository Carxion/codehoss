# %%
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

houses = pd.read_csv("/data/houses.csv")
FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]

# %%
X_train, X_test, y_train, y_test = train_test_split(
    houses[FEATURES], houses["price"], test_size=0.2, random_state=42
)
model = LinearRegression().fit(X_train, y_train)
mae = mean_absolute_error(y_test, model.predict(X_test))
mae
