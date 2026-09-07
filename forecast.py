from datetime import datetime, timedelta
from features import load_features
import matplotlib
matplotlib.use("Agg")   # save-to-file mode, no popup (important on Windows)
import matplotlib.pyplot as plt

from geocoding import geocode, is_in_blr
from spatial import get_road_distance_km
from model import load_model, predict_price
from pricing import VEHICLE_TYPES, DISPLAY_NAMES

# --- tunable constants ---
GRAPH_HOURS = 4          # how far ahead the graph looks
PAST_HOURS = 1           # how much past context to show
STEP_MINUTES = 10        # prediction granularity
WAIT_LIMIT_MINUTES = 60  # only recommend waiting up to this long
SAVINGS_RATE = 1.0    # Rs. saving required per minute of waiting -- tuned by feel for Bangalore, not a sourced number


def build_forecast(model, vehicle_columns, distance, now):
    """Predict price at each step from PAST_HOURS ago to GRAPH_HOURS ahead, per vehicle type."""
    forecast = {vt: [] for vt in VEHICLE_TYPES}
    start_time = now - timedelta(hours=PAST_HOURS)
    total_minutes = (PAST_HOURS + GRAPH_HOURS) * 60
    steps = total_minutes // STEP_MINUTES

    for i in range(steps + 1):
        t = start_time + timedelta(minutes=i * STEP_MINUTES)
        hour = t.hour + t.minute / 60
        is_weekend = t.weekday() >= 5
        for vt in VEHICLE_TYPES:
            price = predict_price(model, vehicle_columns, distance, hour, is_weekend, vt)
            forecast[vt].append((t, price))
    return forecast


def find_wait_recommendation(forecast, vehicle_type, now):
    """Scaled rule: a wait is worth it only if savings beat SAVINGS_RATE * wait_minutes."""
    points = forecast[vehicle_type]
    now_point = min(points, key=lambda tp: abs((tp[0] - now).total_seconds()))
    now_price = now_point[1]

    cutoff = now + timedelta(minutes=WAIT_LIMIT_MINUTES)
    future = [(t, p) for (t, p) in points if now < t <= cutoff]
    if not future:
        return now_price, "Book now"

    best = None
    for t, price in future:
        wait_min = (t - now).total_seconds() / 60
        savings = now_price - price
        margin = savings - SAVINGS_RATE * wait_min   # positive = worth the wait
        if savings > 0 and margin > 0:
            if best is None or margin > best[3]:
                best = (t, price, savings, margin, wait_min)

    if best is None:
        return now_price, "Book now"

    t, price, savings, margin, wait_min = best
    rec = f"Wait {int(wait_min)} min (until {t.strftime('%H:%M')}) for ~Rs.{price:.0f}, save Rs.{savings:.0f}"
    return now_price, rec

def hour_data_density(times, now):
    """Count REAL logged rows (not synthetic) within +/- 0.5h of each forecast time.
    Real data is what tells us the model is grounded vs. echoing the synthetic formula."""
    import csv
    real_hours = []
    try:
        with open("real_prices.csv") as f:
            for row in csv.DictReader(f):
                real_hours.append(float(row["hour"]))
    except FileNotFoundError:
        pass

    counts = []
    for t in times:
        h = t.hour + t.minute / 60
        near = sum(1 for rh in real_hours if abs(rh - h) <= 0.5)
        counts.append(near)
    return counts

def plot_forecast(forecast, pickup_name, drop_name, now, outpath="forecast.png"):
    plt.figure(figsize=(10, 6))

    # use the first vehicle's times as the shared x-axis
    ref_times = [t for t, _ in forecast[next(iter(VEHICLE_TYPES))]]
    density = hour_data_density(ref_times, now)

    # shade regions where training data is sparse (low confidence)
    # threshold: fewer than this many nearby rows = "the model is guessing"
    SPARSE_THRESHOLD = 2
    for i in range(len(ref_times) - 1):
        if density[i] < SPARSE_THRESHOLD:
            plt.axvspan(ref_times[i], ref_times[i + 1], color="red", alpha=0.06)

    for vt in VEHICLE_TYPES:
        points = forecast[vt]
        times = [t for t, _ in points]
        prices = [p for _, p in points]
        plt.plot(times, prices, marker="o", markersize=3, label=DISPLAY_NAMES[vt])

    plt.axvline(now, color="gray", linestyle="--", alpha=0.7)
    plt.text(now, plt.ylim()[1], " now", color="gray", va="top", fontsize=9)

    # a note explaining the shading, so a viewer understands it
    plt.text(0.01, 0.02, "Red shading = sparse training data (lower confidence)",
             transform=plt.gca().transAxes, fontsize=8, color="darkred", alpha=0.8)

    plt.title(f"Price forecast: {pickup_name} -> {drop_name}")
    plt.xlabel("Time")
    plt.ylabel("Estimated price (Rs.)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()
    return outpath


def main():
    pickup_name = input("Pickup location: ").strip()
    drop_name = input("Drop location: ").strip()

    pickup = geocode(pickup_name)
    drop = geocode(drop_name)
    if not pickup or not drop:
        print("Could not find one of those locations.")
        return
    if not is_in_blr(pickup[0], pickup[1]) or not is_in_blr(drop[0], drop[1]):
        print("This tool only works for routes inside Bangalore.")
        return

    distance = get_road_distance_km(pickup[0], pickup[1], drop[0], drop[1])
    if distance is None:
        print("Could not find a drivable route.")
        return

    model, vehicle_columns = load_model()
    now = datetime.now()
    forecast = build_forecast(model, vehicle_columns, distance, now)

    print(f"\n{pickup_name} -> {drop_name} ({distance:.1f} km)\n")
    for vt in VEHICLE_TYPES:
        now_price, rec = find_wait_recommendation(forecast, vt, now)
        print(f"  {DISPLAY_NAMES[vt]:<12} ~Rs.{now_price:.0f}  |  {rec}")

    path = plot_forecast(forecast, pickup_name, drop_name, now)
    print(f"\nForecast graph saved to {path}")
    print("(Estimates from a model, not live Uber quotes.)")


if __name__ == "__main__":
    main()