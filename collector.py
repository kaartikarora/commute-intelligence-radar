import csv
import os
import time
from datetime import datetime

from geocoding import geocode
from spatial import get_road_distance_km
from pricing import estimate_price, VEHICLE_TYPES

CSV_PATH = "watched_routes.csv"
WATCHED_ROUTES = [
    ("Yelahanka", "Bellandur"),
    ("Koramangala", "Indiranagar"),
    ("Yelahanka", "Kempegowda International Airport"),
]

_geocode_cache = {}

def cached_geocode(place):
    if place not in _geocode_cache:
        _geocode_cache[place] = geocode(place)
        time.sleep(1)  # only sleep on an actual new lookup, not a cache hit
    return _geocode_cache[place]

def collect_once():
    now = datetime.now()
    hour = now.hour + now.minute / 60
    is_weekend = now.weekday() >= 5
    is_friday = now.weekday() == 4

    for pickup_name, drop_name in WATCHED_ROUTES:
        pickup = cached_geocode(pickup_name)
        drop = cached_geocode(drop_name)
        if not pickup or not drop:
            continue

        distance = get_road_distance_km(pickup[0], pickup[1], drop[0], drop[1])
        if distance is None:
            continue

        for vehicle_type in VEHICLE_TYPES:
            result = estimate_price(distance, hour, is_weekend, False, vehicle_type, is_friday)
            row = {
                "timestamp": now.isoformat(timespec="minutes"),
                "pickup": pickup_name,
                "dropoff": drop_name,
                "distance_km": round(distance, 2),
                "hour": round(hour, 2),
                "vehicle_type": vehicle_type,
                "price": result["price"],
                "surge": result["surge"],
            }
            file_exists = os.path.exists(CSV_PATH)
            with open(CSV_PATH, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
            print(f"[{row['timestamp']}] {pickup_name}->{drop_name} ({vehicle_type}): Rs.{row['price']} ({row['surge']}x)")

if __name__ == "__main__":
    collect_once()