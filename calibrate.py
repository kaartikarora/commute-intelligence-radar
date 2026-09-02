import csv
from pricing import peak_factor, MIN_SURGE, MAX_SURGE

def estimate_surge(hour, is_weekend, is_rainy, is_friday=False):
    # same surge logic as pricing.py, isolated so we can back it out
    peak = peak_factor(hour, is_friday)
    weekend_damp = 0.5 if is_weekend else 1.0
    raw_signal = min(peak * weekend_damp + (0.3 if is_rainy else 0), 1.0)
    return MIN_SURGE + (MAX_SURGE - MIN_SURGE) * raw_signal

def calibrate(vehicle_type="Mini"):
    with open("real_prices.csv") as f:
        rows = [r for r in csv.DictReader(f)
                if r["vehicle_type"] == vehicle_type
                and not (float(r["hour"]) >= 22 or float(r["hour"]) < 5)]

    if not rows:
        print(f"No real {vehicle_type} data logged yet.")
        return

    print(f"Calibrating {vehicle_type} from {len(rows)} real data points:\n")
    points = []
    for r in rows:
        distance = float(r["distance_km"])
        hour = float(r["hour"])
        is_weekend = r["is_weekend"] == "True"
        is_rainy = r["is_rainy"] == "True"
        real_price = float(r["price"])

        surge = estimate_surge(hour, is_weekend, is_rainy)
        base_price = real_price / surge   # strip surge back out -> implied base fare
        points.append((distance, base_price))
        print(f"  {distance:.1f}km at {hour:.1f}h: real Rs.{real_price:.0f}, "
              f"implied surge {surge:.2f}x, implied base Rs.{base_price:.0f}")

    # fit base_price = base_fare + per_km * distance  (a straight line)
    n = len(points)
    sum_d = sum(d for d, _ in points)
    sum_b = sum(b for _, b in points)
    sum_dd = sum(d * d for d, _ in points)
    sum_db = sum(d * b for d, b in points)

    per_km = (n * sum_db - sum_d * sum_b) / (n * sum_dd - sum_d * sum_d)
    base_fare = (sum_b - per_km * sum_d) / n

    print(f"\nBest-fit for {vehicle_type}:")
    print(f"  base_fare = Rs.{base_fare:.1f}")
    print(f"  per_km    = Rs.{per_km:.1f}")

if __name__ == "__main__":
    calibrate("Mini")