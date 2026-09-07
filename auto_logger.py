"""Automated ground-truth price logger for the commute-radar pipeline."""

import csv
import os
import random
import sys
import time
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright

from geocoding import geocode
from pricing import VEHICLE_TYPES
from spatial import haversine_km, get_road_distance_km
from uber_session import PROFILE_DIR, UBER_URL

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


def get_is_rainy(lat, lon):
    """Returns True if Open-Meteo reports current precipitation at (lat, lon), None on failure."""
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current": "precipitation"},
    )

    if response.status_code != 200:
        return None

    precipitation = response.json().get("current", {}).get("precipitation")

    if precipitation is None:
        return None

    return precipitation > 0.0


class UberAuthError(Exception):
    """Raised when the Uber session looks expired or invalid."""


UBER_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.5',
    'content-type': 'application/json',
    'priority': 'u=1, i',
    'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'x-csrf-token': 'x',
    'x-uber-client-name': 'web-plan',
    'x-uber-rv-initial-load-city-id': '130',
    'x-uber-rv-session-type': 'desktop_session',
}
# 'origin', 'referer', and 'user-agent' are deliberately absent -- real
# browsers manage those automatically and don't let JS override them.
# Manually setting them (as the old requests-based version did) was
# itself a bot-detection signal.

# Tied to this account's saved payment method -- update if it changes.
PAYMENT_PROFILE_UUID = 'd9b6ac92-1645-5423-a91a-c0b5c25d81ea'

UBER_GRAPHQL_QUERY = 'query Products($boostedVehicleId: String, $capacity: Int, $destinations: [InputCoordinate!]!, $hcvContext: InputRVWebCommonHCVContext, $includeRecommended: Boolean = false, $isHcv: Boolean, $isRiderCurrentUser: Boolean, $payment: InputPayment, $paymentProfileUUID: String, $pickup: InputCoordinate!, $pickupFormattedTime: String, $profileType: String, $profileUUID: String, $returnByFormattedTime: String, $stuntID: String, $targetProductType: EnumRVWebCommonTargetProductType) {\n  products(\n    boostedVehicleId: $boostedVehicleId\n    capacity: $capacity\n    destinations: $destinations\n    hcvContext: $hcvContext\n    includeRecommended: $includeRecommended\n    isHcv: $isHcv\n    isRiderCurrentUser: $isRiderCurrentUser\n    payment: $payment\n    paymentProfileUUID: $paymentProfileUUID\n    pickup: $pickup\n    pickupFormattedTime: $pickupFormattedTime\n    profileType: $profileType\n    profileUUID: $profileUUID\n    returnByFormattedTime: $returnByFormattedTime\n    stuntID: $stuntID\n    targetProductType: $targetProductType\n  ) {\n    ...ProductsFragment\n    __typename\n  }\n}\n\nfragment ProductsFragment on RVWebCommonProductsResponse {\n  defaultVVID\n  hourlyTiersWithMinimumFare {\n    ...HourlyTierFragment\n    __typename\n  }\n  intercity {\n    ...IntercityFragment\n    __typename\n  }\n  links {\n    iFrame\n    text\n    url\n    __typename\n  }\n  productsUnavailableMessage\n  tiers {\n    ...TierFragment\n    __typename\n  }\n  __typename\n}\n\nfragment BadgesFragment on RVWebCommonProductBadge {\n  backgroundColor\n  color\n  contentColor\n  icon\n  inactiveBackgroundColor\n  inactiveContentColor\n  text\n  __typename\n}\n\nfragment HourlyTierFragment on RVWebCommonHourlyTier {\n  description\n  distance\n  fare\n  fareAmountE5\n  farePerHour\n  minutes\n  packageVariantUUID\n  preAdjustmentValue\n  __typename\n}\n\nfragment IntercityFragment on RVWebCommonIntercityInfo {\n  oneWayIntercityConfig(destinations: $destinations, pickup: $pickup) {\n    ...IntercityConfigFragment\n    __typename\n  }\n  roundTripIntercityConfig(destinations: $destinations, pickup: $pickup) {\n    ...IntercityConfigFragment\n    __typename\n  }\n  __typename\n}\n\nfragment IntercityConfigFragment on RVWebCommonIntercityConfig {\n  description\n  onDemandAllowed\n  reservePickup {\n    ...IntercityTimePickerFragment\n    __typename\n  }\n  returnBy {\n    ...IntercityTimePickerFragment\n    __typename\n  }\n  __typename\n}\n\nfragment IntercityTimePickerFragment on RVWebCommonIntercityTimePicker {\n  bookingRange {\n    maximum\n    minimum\n    __typename\n  }\n  header {\n    subTitle\n    title\n    __typename\n  }\n  __typename\n}\n\nfragment TierFragment on RVWebCommonProductTier {\n  products {\n    ...ProductFragment\n    __typename\n  }\n  title\n  __typename\n}\n\nfragment ProductFragment on RVWebCommonProduct {\n  badges {\n    ...BadgesFragment\n    __typename\n  }\n  cityID\n  currencyCode\n  description\n  detailedDescription\n  discountPrimary\n  displayName\n  estimatedTripTime\n  etaInMin\n  etaMax\n  etaStringShort\n  fares {\n    capacity\n    discountPrimary\n    fare\n    fareAmountE5\n    hasPromo\n    hasRidePass\n    meta\n    preAdjustmentValue\n    suggestedUpfrontTipAmounts {\n      amount {\n        amountE5\n        currencyCode\n        __typename\n      }\n      displayString\n      __typename\n    }\n    __typename\n  }\n  hasPromo\n  hasRidePass\n  hasBenefitsOnFare\n  hourly {\n    tiers {\n      ...HourlyTierFragment\n      __typename\n    }\n    overageRates {\n      ...HourlyOverageRatesFragment\n      __typename\n    }\n    __typename\n  }\n  iconType\n  id\n  is3p\n  isAvailable\n  legalConsent {\n    ...ProductLegalConsentFragment\n    __typename\n  }\n  parentProductUuid\n  preAdjustmentValue\n  productClassificationTypeName\n  productImageUrl\n  productUuid\n  rankedPricingExplainerText\n  reserveEnabled\n  vehicleViewUuid\n  __typename\n}\n\nfragment ProductLegalConsentFragment on RVWebCommonProductLegalConsent {\n  header\n  image {\n    url\n    width\n    __typename\n  }\n  description\n  enabled\n  ctaUrl\n  ctaDisplayString\n  buttonLabel\n  showOnce\n  shouldBlockRequest\n  __typename\n}\n\nfragment HourlyOverageRatesFragment on RVWebCommonHourlyOverageRates {\n  perDistanceUnit\n  perTemporalUnit\n  __typename\n}\n'

# Runs inside the real browser via page.evaluate() -- 'payload' is
# injected as a real JS object (Playwright serializes the Python dict
# we pass in), so it never needs to be stringified by hand here.
_FETCH_PRODUCTS_JS = """async (payload) => {
    const response = await fetch("https://m.uber.com/go/graphql", {
        method: "POST",
        headers: payload.headers,
        body: JSON.stringify(payload.body),
        credentials: "include",
    });
    return {status: response.status, body: await response.json()};
}"""


def fetch_uber_products(pickup_lat, pickup_lon, drop_lat, drop_lon):
    """Calls Uber's internal GraphQL API and returns the raw 'tiers' list.

    Runs the request from INSIDE a real, authenticated browser context
    (via Playwright) instead of Python's `requests` -- confirmed via a
    console test that Cloudflare's bot detection accepts the browser's
    real fetch() but rejects an identical `requests` call, even with
    matching cookies/headers/payload. `credentials: "include"` means
    the browser supplies its own cookies automatically; nothing needs
    to be extracted or passed in manually.

    Raises UberAuthError if the session looks expired/invalid -- an
    empty fares list on an individual product is NOT an auth error,
    just "unavailable right now" (handled by the caller separately).
    """
    body = {
        'operationName': 'Products',
        'variables': {
            'includeRecommended': False,
            'destinations': [{'latitude': drop_lat, 'longitude': drop_lon}],
            'payment': {'paymentProfileUUID': PAYMENT_PROFILE_UUID, 'uberCashToggleOn': True},
            'paymentProfileUUID': PAYMENT_PROFILE_UUID,
            'pickup': {'latitude': pickup_lat, 'longitude': pickup_lon},
        },
        'query': UBER_GRAPHQL_QUERY,
    }

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=PROFILE_DIR, headless=True)
        page = context.new_page()
        page.goto(UBER_URL)

        result = page.evaluate(_FETCH_PRODUCTS_JS, {"headers": UBER_HEADERS, "body": body})

        context.close()

    if result["status"] != 200:
        raise UberAuthError(f"Uber returned HTTP {result['status']}")

    data = result["body"]

    if "errors" in data:
        raise UberAuthError(f"Uber GraphQL returned errors: {data['errors']}")

    tiers = data.get("data", {}).get("products", {}).get("tiers")

    if tiers is None:
        raise UberAuthError("Response missing data.products.tiers -- session likely expired")

    return tiers


# Confirmed against a live Bangalore response -- real displayName
# values, not guesses. Everything else Uber returns (Black, UberXL,
# Bike, Uber Pet, etc.) is a real product we simply don't track.
UBER_NAME_MAP = {
    "Auto": "Auto",
    "Go Non AC": "Mini",
    "Premier AC": "Sedan",
}


def parse_uber_prices(tiers):
    """Converts Uber's raw tiers list into {internal_vehicle_type: price}.

    Names not in UBER_NAME_MAP are silently skipped -- they're real
    Uber products, just not ones this project tracks, not an error.
    If one of the THREE expected categories is missing at the end,
    THAT'S printed as a warning -- the real signal something changed
    (e.g. Uber renamed "Premier AC" again).
    """
    prices = {}

    for tier in tiers:
        for product in tier["products"]:
            vehicle_type = UBER_NAME_MAP.get(product["displayName"])

            if vehicle_type is None or not product["fares"]:
                continue

            fare_str = product["fares"][0]["fare"]  # e.g. "₹119.92"
            prices[vehicle_type] = float(fare_str.replace("₹", "").replace(",", ""))

    for vehicle_type in VEHICLE_TYPES:
        if vehicle_type not in prices:
            print(f"Warning: no price found for '{vehicle_type}' -- Uber may have renamed this tier.")

    return prices


CSV_PATH = "real_prices.csv"
FIELDNAMES = ["timestamp", "pickup", "dropoff", "distance_km", "hour",
              "is_weekend", "is_rainy", "vehicle_type", "price"]


def write_prices(route, prices, is_rainy):
    """Appends one row per vehicle type to real_prices.csv -- same
    schema manual_logger.py already writes, so features.py needs no
    changes to pick these rows up."""
    now = datetime.now()
    file_exists = os.path.exists(CSV_PATH)

    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for vehicle_type, price in prices.items():
            writer.writerow({
                "timestamp": now.isoformat(timespec="minutes"),
                "pickup": route["pickup"],
                "dropoff": route["dropoff"],
                "distance_km": route["distance_km"],
                "hour": round(now.hour + now.minute / 60, 2),
                "is_weekend": now.weekday() >= 5,
                "is_rainy": is_rainy,
                "vehicle_type": vehicle_type,
                "price": price,
            })


def main():
    print(f"\n=== Run at {datetime.now().isoformat(timespec='seconds')} ===")

    routes = pick_routes()

    for route in routes:
        pickup_coords = geocode(f"{route['pickup']}, Bangalore")
        drop_coords = geocode(f"{route['dropoff']}, Bangalore")

        if not pickup_coords or not drop_coords:
            print(f"Could not geocode {route['pickup']} -> {route['dropoff']} -- skipping.")
            continue

        is_rainy = get_is_rainy(pickup_coords[0], pickup_coords[1])

        try:
            tiers = fetch_uber_products(pickup_coords[0], pickup_coords[1], drop_coords[0], drop_coords[1])
        except UberAuthError as e:
            print(f"Uber session error: {e}")
            print("Stopping this run -- session likely needs re-login (run uber_session.login()).")
            sys.exit(1)

        prices = parse_uber_prices(tiers)

        if not prices:
            print(f"No prices found for {route['pickup']} -> {route['dropoff']} -- skipping.")
            continue

        write_prices(route, prices, is_rainy)
        print(f"Logged [{route['band']}] {route['pickup']} -> {route['dropoff']}: {prices}")


if __name__ == "__main__":
    main()
