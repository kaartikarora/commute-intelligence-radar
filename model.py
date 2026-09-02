from datetime import datetime, timedelta
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

from features import load_features

MODEL_PATH = "surge_model.pkl"

def train():
    X, y, vehicle_columns = load_features()

    # hold back 20% of rows -- the model never sees these during training
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)   # this is the actual "learning" step

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    print(f"MAE on held-out test data: {mae:.2f} ")

    joblib.dump({"model": model, "vehicle_columns": vehicle_columns}, MODEL_PATH)
    print(f"Saved trained model to {MODEL_PATH}")
    importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\nFeature importance:")
    print(importances)
    return model, vehicle_columns

def load_model():
    saved = joblib.load(MODEL_PATH)
    return saved["model"], saved["vehicle_columns"]

def predict_price(model, vehicle_columns, distance_km, hour, is_weekend, vehicle_type):
    row = {
        "distance_km": distance_km,
        "hour": hour,
        "is_weekend": int(is_weekend),
    }
    # rebuild the one-hot columns: the matching vehicle is 1, all others 0
    for col in vehicle_columns:
        row[col] = 1 if col == f"vt_{vehicle_type}" else 0

    X_one = pd.DataFrame([row])
    return model.predict(X_one)[0]
if __name__ == "__main__":
    train()

    model, vehicle_columns = load_model()

    tests = [
        (5.7, 13.0, False, "Mini"),   # short-ish midday Mini
        (5.7, 19.0, False, "Mini"),   # same route, evening peak -- should cost MORE
        (30.0, 19.0, False, "Sedan"), # long airport-ish Sedan at peak -- should be pricey
        (5.7, 3.0, False, "Auto"),    # short Auto at 3am -- night surcharge territory
    ]
    print("\nSanity check:")
    for distance, hour, weekend, vt in tests:
        price = predict_price(model, vehicle_columns, distance, hour, weekend, vt)
        print(f"  {distance}km {vt} at {hour:02.0f}:00 -> Rs.{price:.0f}")