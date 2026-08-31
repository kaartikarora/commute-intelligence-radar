import csv
import os
from datetime import datetime

from geocoding import geocode
from spatial import get_road_distance_km
from pricing import VEHICLE_TYPES
CSV_PATH="real_prices.csv"

def main():
    pickup_name=input("Pickup Location: ").strip()
    drop_name=input("Drop Location ").strip()

    pickup=geocode(pickup_name)
    drop=geocode(drop_name)

    if not pickup or not drop:
        print("Could not find one of these locations")
        return
    distance= get_road_distance_km(pickup[0], pickup[1], drop[0], drop[1])
    is_rainy=input("Raining right now? (y/n): ").strip().lower()=='y'
    now=datetime.now()

    fieldnames = ["timestamp", "pickup", "dropoff", "distance_km", "hour",
                  "is_weekend", "is_rainy", "vehicle_type", "price"]

    file_exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        logged = 0
        for vehicle_type in VEHICLE_TYPES:
            price_input = input(f"Price for {vehicle_type} (blank if not shown): Rs.").strip()
            if not price_input:
                continue  # not offered at this location/time -- skip, don't log a fake row

            writer.writerow({
                "timestamp": now.isoformat(timespec="minutes"),
                "pickup": pickup_name,
                "dropoff": drop_name,
                "distance_km": round(distance, 2) if distance else None,
                "hour": round(now.hour + now.minute / 60, 2),
                "is_weekend": now.weekday() >= 5,
                "is_rainy": is_rainy,
                "vehicle_type": vehicle_type,
                "price": float(price_input),
            })
            logged += 1

    print(f"Logged {logged} vehicle type(s) for {pickup_name} -> {drop_name}")

if __name__ == "__main__":
    main()
