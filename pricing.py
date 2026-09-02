import math
MIN_SURGE = 0.5
MAX_SURGE = 2.0

VEHICLE_TYPES = {
    "Auto":  {"base_fare": 40, "per_km": 20, "night_surcharge": True},
    "Mini":  {"base_fare": 40, "per_km": 12, "night_surcharge": False},
    "Sedan": {"base_fare": 60, "per_km": 16, "night_surcharge": False},

}
DISPLAY_NAMES = {
    "Auto": "Auto",
    "Mini": "Non-AC",
    "Sedan": "Premier AC",
}
def peak_factor(hour, is_friday=False):
    morning=math.exp(-((hour-9)**2)/(2*1.2**2))*1.0
    evening = math.exp(-((hour - 19.5) ** 2) / (2 * 1.5 ** 2)) * 1.27
    peak=max(morning,evening)

    if is_friday and 17<=hour<=19:
        peak *= 1.15
    return peak
def estimate_price(distance_km, hour, is_weekend, is_rainy, vehicle_type="Mini", is_friday=False):
    cfg = VEHICLE_TYPES[vehicle_type]
    base = cfg["base_fare"] + cfg["per_km"] * distance_km

    if cfg["night_surcharge"] and (hour >= 22 or hour < 5):
        base *= 1.5

    peak = peak_factor(hour, is_friday)
    weekend_damp = 0.5 if is_weekend else 1.0
    raw_signal = min(peak * weekend_damp + (0.3 if is_rainy else 0), 1.0)
    surge = MIN_SURGE + (MAX_SURGE - MIN_SURGE) * raw_signal


    return {"price": round(base * surge, 2), "surge": round(surge, 2), "base": round(base, 2), "is_estimate": True}

if __name__ == "__main__":
    print(estimate_price(5.3, 18.5, is_weekend=False, is_rainy=False, vehicle_type="Mini"))