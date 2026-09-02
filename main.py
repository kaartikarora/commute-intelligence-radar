from datetime import datetime

from geocoding import geocode, is_in_blr
from spatial import get_road_distance_km
from model import load_model, predict_price
from pricing import VEHICLE_TYPES

def main():
    pickup_name = input("Pickup location: ").strip()
    drop_name = input("Drop location: ").strip()

    pickup = geocode(pickup_name)
    drop = geocode(drop_name)
    if not pickup or not drop:
        print("Could not find one of those locations.")
        return

    # both points must be inside Bangalore
    if not is_in_blr(pickup[0], pickup[1]) or not is_in_blr(drop[0], drop[1]):
        print("Sorry -- this tool only works for routes inside Bangalore.")
        return

    distance = get_road_distance_km(pickup[0], pickup[1], drop[0], drop[1])
    if distance is None:
        print("Could not find a drivable route between those points.")
        return

    model, vehicle_columns = load_model()

    now = datetime.now()
    hour = now.hour + now.minute / 60
    is_weekend = now.weekday() >= 5

    print(f"\n{pickup_name} -> {drop_name}")
    print(f"Road distance: {distance:.1f} km")
    print(f"Estimated prices right now ({now.strftime('%A %H:%M')}):\n")

    from pricing import DISPLAY_NAMES   # (or add to the existing pricing import at the top)

    for vehicle_type in VEHICLE_TYPES:
        price = predict_price(model, vehicle_columns, distance, hour, is_weekend, vehicle_type)
        label = DISPLAY_NAMES[vehicle_type]
        print(f"  {label:<12} ~Rs.{price:.0f}")

    print("\n(These are model estimates, not live Uber quotes.)")

if __name__=="__main__":
    main()