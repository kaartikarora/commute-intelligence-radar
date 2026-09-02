import csv
from pricing import estimate_price

def load_real_rows(path="real_prices.csv"):
    with open(path) as f:
        return list(csv.DictReader(f))

def compare_all():
    rows = load_real_rows()
    print(f"{'Route':<45}{'Vehicle':<8}{'Predicted':<12}{'Real':<10}{'Implied surge'}")

    for row in rows:
        distance = float(row["distance_km"])
        hour = float(row["hour"])
        is_weekend = row["is_weekend"] == "True"   # CSV stores this as the literal text "True"/"False"
        is_rainy = row["is_rainy"] == "True"
        vehicle_type = row["vehicle_type"]
        real_price = float(row["price"])

        result = estimate_price(distance, hour, is_weekend, is_rainy, vehicle_type)

        # back out what "surge" the real price implies, same algebra as last time

        implied_surge = real_price / result["base"]

        route = f"{row['pickup']} -> {row['dropoff']}"
        print(f"{route:<45}{vehicle_type:<8}Rs.{result['price']:<10.2f}Rs.{real_price:<8.2f}{implied_surge:.2f}x")

if __name__ == "__main__":
    compare_all()