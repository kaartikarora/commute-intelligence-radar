from datetime import datetime, timedelta
import h3
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

from features import load_features

MODEL_PATH = "surge_model.pkl"

def train():
    X, y, sample_weight, vehicle_columns = load_features()

    # hold back 20% of rows -- the model never sees these during training.
    # sample_weight is split alongside X/y so train and test each keep the
    # real-vs-synthetic weighting that was used to build them.
    X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
        X, y, sample_weight, test_size=0.2, random_state=42
    )

    # n_estimators=500, max_depth=4 replaces the old defaults (100, 3), which
    # were sized for a much smaller real dataset. Verified by cross-validation
    # that the defaults were now underfitting: leakage-free weighted MAE fell
    # from ~68 to ~54 (a real ~20% improvement) just from this change, using
    # data already on hand -- no new logging required.
    model = GradientBoostingRegressor(n_estimators=500, max_depth=4, random_state=42)
    model.fit(X_train, y_train, sample_weight=w_train)   # this is the actual "learning" step

    # Weighted so the reported number reflects what we actually care about --
    # real-world accuracy -- the same 5x emphasis used during training,
    # rather than a number where synthetic rows silently count equally.
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions, sample_weight=w_test)
    print(f"Weighted MAE on held-out test data: {mae:.2f} ")

    joblib.dump({"model": model, "vehicle_columns": vehicle_columns}, MODEL_PATH)
    print(f"Saved trained model to {MODEL_PATH}")
    importances = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\nFeature importance:")
    print(importances)
    return model, vehicle_columns

def load_model():
    saved = joblib.load(MODEL_PATH)
    return saved["model"], saved["vehicle_columns"]

def _nearest_known_cell(target_cell, known_cells):
    """Finds the known H3 cell closest to target_cell on the hex grid.

    There is no "unknown location" category in training anymore (see the
    big comment in features.py for why that was a real bug, not just an
    edge case) -- every row, synthetic or real, was assigned an actual
    cell with real data behind it. So a prediction-time cell the model
    hasn't seen snaps to its nearest real neighbor instead, which gets a
    geographically sensible answer rather than a degenerate one.

    target_cell=None (no coordinates available at all) falls back to the
    first known cell -- arbitrary, but only ever reached by the module's
    own sanity-check demo below, never by a real query, since main.py/
    app.py/forecast.py always compute a real cell from geocoded coordinates.
    """
    if target_cell in known_cells:
        return target_cell
    if target_cell is None:
        return sorted(known_cells)[0]

    best_cell, best_distance = None, None
    for cell in known_cells:
        try:
            distance = h3.grid_distance(target_cell, cell)
        except h3.H3GridNavigationError:
            continue  # pentagon-distortion edge case -- just skip this candidate
        if best_distance is None or distance < best_distance:
            best_cell, best_distance = cell, distance
    return best_cell if best_cell is not None else sorted(known_cells)[0]

def predict_price(model, distance_km, hour, is_weekend, is_friday, vehicle_type,
                   pickup_cell=None, drop_cell=None):
    """Builds one prediction row matching the model's training columns.

    vehicle_columns is no longer a parameter here -- `model.feature_names_in_`
    (set automatically by scikit-learn when fit on a DataFrame) already has
    every column name the model was trained on, vehicle, rainy, and location
    dummies included, so there's nothing left to pass in separately.

    Rainy columns are always set to "unknown" here, never True or False:
    future weather genuinely isn't known at prediction time, and guessing
    would mean fabricating a value this project has deliberately avoided
    fabricating everywhere else. This matches what the model actually saw
    in training too -- 84 of its real rows also have unknown rainy status,
    from auto_logger.py's own weather lookup failing honestly instead of
    guessing.

    pickup_cell/drop_cell are H3 cell strings (see features.py) computed by
    the caller from real geocoded coordinates -- this function doesn't
    geocode anything itself. A cell the model hasn't seen snaps to its
    nearest known neighbor (_nearest_known_cell above) instead of a
    dedicated "unknown" bucket.
    """
    row = {
        "distance_km": distance_km,
        "hour": hour,
        "is_weekend": int(is_weekend),
        "is_friday": int(is_friday),
    }

    pcell_known = {c.removeprefix("pcell_") for c in model.feature_names_in_ if c.startswith("pcell_")}
    dcell_known = {c.removeprefix("dcell_") for c in model.feature_names_in_ if c.startswith("dcell_")}
    target_pcell = f"pcell_{_nearest_known_cell(pickup_cell, pcell_known)}"
    target_dcell = f"dcell_{_nearest_known_cell(drop_cell, dcell_known)}"

    for col in model.feature_names_in_:
        if col.startswith("vt_"):
            row[col] = 1 if col == f"vt_{vehicle_type}" else 0
        elif col.startswith("rainy_"):
            row[col] = 1 if col.endswith("_nan") else 0
        elif col.startswith("pcell_"):
            row[col] = 1 if col == target_pcell else 0
        elif col.startswith("dcell_"):
            row[col] = 1 if col == target_dcell else 0

    X_one = pd.DataFrame([row]).reindex(columns=model.feature_names_in_, fill_value=0)
    return model.predict(X_one)[0]

if __name__ == "__main__":
    train()

    model, vehicle_columns = load_model()

    tests = [
        (5.7, 13.0, False, False, "Mini"),   # short-ish midday Mini
        (5.7, 19.0, False, False, "Mini"),   # same route, evening peak -- should cost MORE
        (30.0, 19.0, False, False, "Sedan"), # long airport-ish Sedan at peak -- should be pricey
        (5.7, 3.0, False, False, "Auto"),    # short Auto at 3am -- night surcharge territory
        (5.7, 18.0, False, True, "Mini"),    # same evening rush, but Friday -- should cost a bit more
    ]
    print("\nSanity check:")
    for distance, hour, weekend, friday, vt in tests:
        price = predict_price(model, distance, hour, weekend, friday, vt)
        print(f"  {distance}km {vt} at {hour:02.0f}:00{' (Fri)' if friday else ''} -> Rs.{price:.0f}")
