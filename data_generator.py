import random
import time
import csv
from datetime import datetime, timedelta

from geocoding import bangalore_bounds
from spatial import haversine_km, get_road_distance_km
from pricing import estimate_price, VEHICLE_TYPES

def random_point(rng):
    lat = rng.uniform(bangalore_bounds["min_lat"], bangalore_bounds["max_lat"])
    lon = rng.uniform(bangalore_bounds["min_lon"], bangalore_bounds["max_lon"])
    return lat, lon

def random_timestamp(rng, days=30):
    end = datetime.now()
    start = end - timedelta(days=days)
    delta_seconds = int((end - start).total_seconds())
    offset = rng.randint(0, delta_seconds)
    return start + timedelta(seconds=offset)

def generate_row(rng):
    dt = random_timestamp(rng)
    p1 = random_point(rng)
    p2 = random_point(rng)

    straight_line = haversine_km(p1[0], p1[1], p2[0], p2[1])
    if straight_line < 1:
        return None  # cheap pre-check -- skip near-duplicate points before spending an OSRM call

    distance = get_road_distance_km(p1[0], p1[1], p2[0], p2[1])
    time.sleep(1)  # respect OSRM's 1 req/sec fair-use limit
    if distance is None:
        return None

    hour = dt.hour + dt.minute / 60
    vehicle_type = rng.choice(list(VEHICLE_TYPES.keys()))
    result = estimate_price(distance, hour, dt.weekday() >= 5, rng.random() < 0.1, vehicle_type, dt.weekday() == 4)

    return {
        "timestamp": dt.isoformat(timespec="minutes"),
        "distance_km": round(distance, 2),
        "hour": round(hour, 2),
        "is_weekend": dt.weekday() >= 5,
        "vehicle_type": vehicle_type,
        "price": result["price"],
        "surge": result["surge"],
    }

if __name__ == "__main__":
    rng = random.Random(42)
    rows = []
    while len(rows) < 500:
        row = generate_row(rng)
        if row:
            rows.append(row)
        print(f"{len(rows)}/500 rows generated", end="\r")

    with open("training_data.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows")