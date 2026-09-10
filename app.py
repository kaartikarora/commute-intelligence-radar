from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

from geocoding import geocode, is_in_blr
from spatial import get_road_distance_km
from model import load_model, predict_price
from pricing import VEHICLE_TYPES, DISPLAY_NAMES
from forecast import build_forecast, find_wait_recommendation

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model, vehicle_columns = load_model()


class RouteRequest(BaseModel):
    pickup: str
    drop: str


@app.get("/")
def home():
    return {"message": "Commute Intelligence Radar is running"}


@app.post("/predict")
def predict(req: RouteRequest):
    pickup = geocode(req.pickup)
    drop = geocode(req.drop)
    if not pickup or not drop:
        return {"error": "Could not find one of those locations."}
    if not is_in_blr(pickup[0], pickup[1]) or not is_in_blr(drop[0], drop[1]):
        return {"error": "This tool only works for routes inside Bangalore."}

    distance = get_road_distance_km(pickup[0], pickup[1], drop[0], drop[1])
    if distance is None:
        return {"error": "Could not find a drivable route."}

    now = datetime.now()
    forecast = build_forecast(model, vehicle_columns, distance, now)

    # build the response: for each vehicle, current price + wait rec + the full curve
    results = []
    for vt in VEHICLE_TYPES:
        now_price, rec = find_wait_recommendation(forecast, vt, now)
        # convert the forecast curve into JSON-friendly time/price points
        curve = [
            {"time": t.strftime("%H:%M"), "price": round(p, 2)}
            for (t, p) in forecast[vt]
        ]
        results.append({
            "vehicle": DISPLAY_NAMES[vt],
            "current_price": round(now_price, 2),
            "recommendation": rec,
            "forecast": curve,
        })

    return {
        "pickup": req.pickup,
        "drop": req.drop,
        "distance_km": round(distance, 2),
        "results": results,
    }