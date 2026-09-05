"""Automated ground-truth price logger for the commute-radar pipeline."""

import csv
import random

from geocoding import geocode
from spatial import haversine_km, get_road_distance_km

HUB_CSV = "bangalore_hubs.csv"

# (minimum_km, maximum_km) per route size we want one of each run.
DISTANCE_BANDS = {
    "short": (2, 9.9),
    "medium": (10, 17.9),
    "long": (18, 45),
}

MAX_ATTEMPTS_PER_BAND = 30  # retry cap so a thin pool can't hang the run


def load_hub_names():
    """Returns the place-name pool built by blr_hubs.py."""
    names = []
    with open(HUB_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            names.append(row["name"])
    return names


def check_distance_band(pickup_name, drop_name, band):
    """Returns the road distance in km if it falls in `band`, else None."""
    min_km, max_km = DISTANCE_BANDS[band]

    # Append the city to disambiguate names that recur elsewhere in India.
    pickup = geocode(f"{pickup_name}, Bangalore")
    drop = geocode(f"{drop_name}, Bangalore")

    if not pickup or not drop:
        return None

    # Cheap reject: road distance is never shorter than straight-line,
    # so an already-too-far straight line rules out this pair for free.
    straight_line = haversine_km(pickup[0], pickup[1], drop[0], drop[1])
    if straight_line > max_km:
        return None

    # No equivalent cheap reject on the lower bound -- road circuity can
    # push a short straight-line pair into a longer real route.
    road_distance = get_road_distance_km(pickup[0], pickup[1], drop[0], drop[1])
    if road_distance is None:
        return None

    if min_km <= road_distance <= max_km:
        return road_distance

    return None


def pick_routes():
    """Picks one route per distance band via rejection sampling.

    Returns a list of {"band", "pickup", "dropoff", "distance_km"} dicts,
    one per band that found a match within MAX_ATTEMPTS_PER_BAND.
    """
    hub_names = load_hub_names()
    routes = []

    for band in DISTANCE_BANDS:
        for attempt in range(MAX_ATTEMPTS_PER_BAND):
            pickup_name, drop_name = random.sample(hub_names, 2)
            distance = check_distance_band(pickup_name, drop_name, band)

            if distance is not None:
                routes.append({
                    "band": band,
                    "pickup": pickup_name,
                    "dropoff": drop_name,
                    "distance_km": round(distance, 2),
                })
                break
        else:
            print(f"Could not find a '{band}' route after {MAX_ATTEMPTS_PER_BAND} attempts -- skipping.")

    return routes


if __name__ == "__main__":
    routes = pick_routes()
    for route in routes:
        print(f"[{route['band']}] {route['pickup']} -> {route['dropoff']} ({route['distance_km']} km)")
