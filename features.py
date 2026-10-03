import pandas as pd

def load_synthetic(path="training_data.csv"):
    df = pd.read_csv(path)
    df["source"] = "synthetic"
    return df[["timestamp", "distance_km", "hour", "is_weekend", "is_rainy", "vehicle_type", "price", "source"]]

def load_real(path="real_prices.csv"):
    df = pd.read_csv(path)
    df["source"] = "real"
    return df[["timestamp", "distance_km", "hour", "is_weekend", "is_rainy", "vehicle_type", "price", "source"]]

def load_features(real_weight=5):
    """Builds the model's feature matrix, target, per-row sample weights,
    and the list of one-hot vehicle-type columns.

    Real rows matter more than synthetic ones for real-world accuracy, so
    they're weighted `real_weight` times as heavily during training. This
    used to be done by physically duplicating each real row `real_weight`
    times BEFORE the train/test split -- which meant identical copies of
    the same real fare could land in both the training set and the test
    set, letting the model partly "memorize" what it was being tested on.
    Measured effect: naive single-split MAE read ~61, but a leakage-free
    evaluation (GroupKFold, keeping all copies of a row on the same side
    of the split) gave ~68, with much higher fold-to-fold variance (5.77
    vs 1.14) -- the old number was both optimistic and noisier than it
    looked. Passing `sample_weight` to the model instead gets the same
    "real data matters 5x more" effect with no duplication and no leak,
    since every real row still appears exactly once.
    """
    synthetic = load_synthetic()
    real = load_real()

    combined = pd.concat([synthetic, real], ignore_index=True)
    combined["is_weekend"] = combined["is_weekend"].astype(bool).astype(int)

    # is_friday is derived from timestamp (not stored directly) so it's
    # available identically for both synthetic and real rows. The synthetic
    # price formula (pricing.py) already factors in a Friday evening bump;
    # without this feature the model had no way to explain that bump,
    # which showed up as unexplainable noise on ~1/7 of synthetic rows.
    combined["timestamp"] = pd.to_datetime(combined["timestamp"])
    combined["is_friday"] = (combined["timestamp"].dt.weekday == 4).astype(int)

    features = combined[["distance_km", "hour", "is_weekend", "is_friday"]].copy()

    vehicle_dummies = pd.get_dummies(combined["vehicle_type"], prefix="vt")
    features = pd.concat([features, vehicle_dummies], axis=1)

    # is_rainy is a real column in real_prices.csv that used to be dropped
    # entirely. Some real rows have it as NaN (the weather lookup failed at
    # logging time and was honestly recorded as "unknown" rather than
    # guessed -- see auto_logger.py's get_is_rainy). dummy_na=True turns
    # that into its own explicit "unknown" column instead of silently
    # coercing it to False, matching this project's fail-open-to-unknown
    # principle: never fabricate a value you don't actually have.
    rainy_dummies = pd.get_dummies(combined["is_rainy"], prefix="rainy", dummy_na=True)
    features = pd.concat([features, rainy_dummies], axis=1)

    target = combined["price"]
    sample_weight = combined["source"].map({"real": real_weight, "synthetic": 1}).astype(float)

    return features, target, sample_weight, list(vehicle_dummies.columns)

if __name__ == "__main__":
    X, y, sample_weight, vehicle_columns = load_features()
    print(X.head())
    print("Vehicle columns:", vehicle_columns)
    print("Total rows:", len(X))
    print("Sample weight counts:", sample_weight.value_counts().to_dict())
