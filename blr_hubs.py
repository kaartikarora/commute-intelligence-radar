"""
build_hub_pool.py

ONE-TIME script (run it once, rerun only if you want to refresh/expand
coverage later). It queries OpenStreetMap's Overpass API for real,
named localities inside Bangalore, and saves the list locally so
auto_logger.py can pick random pickup/drop names from real places
instead of made-up ones or raw random coordinates that might land in
a lake or a highway median.

Why Overpass and not Nominatim here: Nominatim (used elsewhere in this
project via geocoding.py) is built for "look up THIS specific name" --
it's not designed for "give me EVERY place matching a category inside
this area." Overpass is a different OSM service built exactly for
that kind of bulk/category query.
"""

import csv
import requests
from geocoding import bangalore_bounds
import re


OVERPASS_URL = "https://lz4.overpass-api.de/api/interpreter"
OUTPUT_CSV = "bangalore_hubs.csv"


HEADERS = {
    "User-Agent": "CommuteIntelligenceRadar/1.0 (kaartikrajarora2005@gmail.com)"
}


# Matches names that are JUST a generic layout label with no actual
# place name attached -- e.g. "1st Block", "2nd Phase", "Block 5".
# Deliberately does NOT match "12th Block Nagarbhavi" or "5th Phase
# JP Nagar" -- those carry a real place name too, so they stay.
GENERIC_PATTERNS = [
    re.compile(r'^\d+(st|nd|rd|th)?\s+(Block|Phase|Stage|Cross|Main|Sector|Layout)s?$', re.IGNORECASE),
    re.compile(r'^(Block|Phase|Stage|Cross|Main|Sector|Layout)\s*\d+$', re.IGNORECASE),
]

def is_too_generic(name):
    name = name.strip()
    return any(pattern.match(name) for pattern in GENERIC_PATTERNS)
def build_query():

    bbox = (
        f'{bangalore_bounds["min_lat"]},{bangalore_bounds["min_lon"]},'
        f'{bangalore_bounds["max_lat"]},{bangalore_bounds["max_lon"]}'
    )


    query = f"""
    [out:json][timeout:25];
    (
      node["place"="suburb"]({bbox});
      node["place"="neighbourhood"]({bbox});
      node["place"="quarter"]({bbox});
    );
    out body;
    """
    return query


def fetch_hub_names():

    query = build_query()

    response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS)


    if response.status_code != 200:
        print(f"Overpass request failed: HTTP {response.status_code}")
        return []

    data = response.json()
    elements = data.get("elements", [])


    names = set()
    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name")
        if name and not is_too_generic(name):
            names.add(name)

    return sorted(names)


def save_hub_names(names):

    #Writes the list of names to a simple one-column CSV file.

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name"])
        for name in names:
            writer.writerow([name])


if __name__ == "__main__":
    hub_names = fetch_hub_names()
    print(f"Fetched {len(hub_names)} named localities from Overpass.")

    if hub_names:
        save_hub_names(hub_names)
        print(f"Saved to {OUTPUT_CSV}")
    else:
        print("Nothing to save -- check the error above.")