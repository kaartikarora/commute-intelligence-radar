import pandas as pd

def load_synthetic(path="training_data.csv"):
    df = pd.read_csv(path)
    df["source"] = "synthetic"
    return df[["distance_km", "hour", "is_weekend", "vehicle_type", "price", "source"]]

def load_real(path="real_prices.csv"):
    df = pd.read_csv(path)
    df["source"] = "real"
    return df[["distance_km", "hour", "is_weekend", "vehicle_type", "price", "source"]]

def load_features(real_weight=5):
    synthetic = load_synthetic()
    real = load_real()

    real_weighted = pd.concat([real] * real_weight, ignore_index=True)
    combined = pd.concat([synthetic, real_weighted], ignore_index=True)
    combined["is_weekend"] = combined["is_weekend"].astype(bool).astype(int)

    features = combined[["distance_km", "hour", "is_weekend"]].copy()
    vehicle_dummies = pd.get_dummies(combined["vehicle_type"], prefix="vt")
    features = pd.concat([features, vehicle_dummies], axis=1)

    target = combined["price"]
    return features, target, list(vehicle_dummies.columns)

if __name__ == "__main__":
    X, y, vehicle_columns = load_features()
    print(X.head())
    print("Vehicle columns:", vehicle_columns)
    print("Total rows:", len(X))