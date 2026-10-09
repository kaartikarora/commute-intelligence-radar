import numpy as np
import pandas as pd

from spatial import to_h3

HUB_CELL_RESOLUTION = 6
HUB_COORDS_CACHE = "hub_coords_cache.csv"

def load_synthetic(path="training_data.csv"):
    df = pd.read_csv(path)
    df["source"] = "synthetic"
    # Synthetic rows have no real place name -- they were generated from
    # random lat/lon points that were never saved (see data_generator.py).
    # pickup/dropoff stay missing so the location features below correctly
    # fall back to "unknown" for every synthetic row.
    df["pickup"] = None
    df["dropoff"] = None
    return df[["timestamp", "distance_km", "hour", "is_weekend", "is_rainy", "vehicle_type", "pickup", "dropoff", "price", "source"]]

def load_real(path="real_prices.csv"):
    df = pd.read_csv(path)
    df["source"] = "real"
    return df[["timestamp", "distance_km", "hour", "is_weekend", "is_rainy", "vehicle_type", "pickup", "dropoff", "price", "source"]]

def _load_hub_cells(resolution=HUB_CELL_RESOLUTION):
    """name -> H3 cell, from the geocoded coordinate cache.

    Built once by geocoding every unique pickup/dropoff name that has
    appeared in real_prices.csv (see the one-off scratchpad script that
    produced hub_coords_cache.csv -- regenerate it the same way if new
    hub names show up that aren't in the cache yet).
    """
    cache = pd.read_csv(HUB_COORDS_CACHE)
    return {
        row["name"]: to_h3(row["lat"], row["lon"], resolution=resolution)
        for _, row in cache.iterrows()
    }

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

    # Location: distance_km alone treats every route the same regardless of
    # which part of Bangalore it's actually in. H3 hex cells (resolution 6,
    # ~36 sq km each -- roughly neighborhood-sized) let the model learn
    # "this area tends to run higher/lower than its distance alone would
    # predict." Tested empirically before adding: resolution 8 (this
    # project's usual default) was tried first and was too fine-grained --
    # 136 cells across ~600 sample rows, most with only 1-3 rows, far too
    # sparse to learn anything from. Resolution 6 (33 cells, median ~20
    # rows/cell) measurably helped: weighted MAE 54.66 -> 51.39 in
    # cross-validation, with LOWER variance too, not just a lower mean.
    #
    # An earlier version gave synthetic rows (which have no real coordinates
    # -- see load_synthetic above) an explicit "unknown" cell, following the
    # same fail-open-to-unknown principle as is_rainy above. That turned out
    # to be a real mistake, not just a style choice: "unknown" became a
    # dedicated one-hot category populated ONLY by 500 low-weight synthetic
    # rows, and with enough tree capacity to fit that small a slice closely,
    # predictions for it swung wildly and nonsensically (Rs.12 to Rs.332 for
    # the same 5.7km Mini trip across different hours). Any live user asking
    # about a location outside the ~720 known hubs would have landed exactly
    # in that broken bucket -- is_rainy's NaN rows don't have this problem
    # because real NaN rows genuinely share the same unknowable situation a
    # future prediction is in, but no real row is ever truly "nowhere."
    #
    # Fix: there's no "unknown" category at all. Synthetic rows are
    # deterministically assigned a cell sampled from the REAL pickup/drop
    # cell distribution (proportional to how often each real cell actually
    # appears), so every synthetic row lands in a cell with real, well-
    # supported data to be regularized by. At prediction time (model.py's
    # predict_price), a cell the model has never seen snaps to its nearest
    # known neighbor via h3.grid_distance rather than falling into a
    # separate bucket.
    hub_cells = _load_hub_cells()
    real_mask = combined["source"] == "real"
    real_pickup_cells = combined.loc[real_mask, "pickup"].map(hub_cells)
    real_drop_cells = combined.loc[real_mask, "dropoff"].map(hub_cells)

    rng = np.random.RandomState(42)
    n_synthetic = (~real_mask).sum()
    synthetic_pickup_cells = rng.choice(real_pickup_cells.dropna(), size=n_synthetic)
    synthetic_drop_cells = rng.choice(real_drop_cells.dropna(), size=n_synthetic)

    pickup_cell = pd.Series(index=combined.index, dtype=object)
    pickup_cell[real_mask] = real_pickup_cells
    pickup_cell[~real_mask] = synthetic_pickup_cells

    drop_cell = pd.Series(index=combined.index, dtype=object)
    drop_cell[real_mask] = real_drop_cells
    drop_cell[~real_mask] = synthetic_drop_cells

    pickup_dummies = pd.get_dummies(pickup_cell, prefix="pcell")
    drop_dummies = pd.get_dummies(drop_cell, prefix="dcell")
    features = pd.concat([features, pickup_dummies, drop_dummies], axis=1)

    target = combined["price"]
    sample_weight = combined["source"].map({"real": real_weight, "synthetic": 1}).astype(float)

    return features, target, sample_weight, list(vehicle_dummies.columns)

if __name__ == "__main__":
    X, y, sample_weight, vehicle_columns = load_features()
    print(X.head())
    print("Vehicle columns:", vehicle_columns)
    print("Total rows:", len(X))
    print("Total features:", X.shape[1])
    print("Sample weight counts:", sample_weight.value_counts().to_dict())
