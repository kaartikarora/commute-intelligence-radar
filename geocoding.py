import requests

def geocode(place_name):
    url="https://nominatim.openstreetmap.org/search"
    params={
        "q":place_name,
        "format":"json"
    }
    headers={
        "User-Agent": "CommuteIntelligenceRadar/1.0(kaartikrajarora2005@gmail.com)"
    }
    response= requests.get(url, params=params, headers=headers)
    data=response.json()
    if not data:
        return None
    lat=float(data[0]["lat"])
    lon=float(data[0]["lon"])
    return lat, lon
if __name__=="__main__":
    result=geocode("Indiranagar, Bangalore")
    print(result)
bangalore_bounds={    
    "min_lat":12.83,
    "max_lat":13.14,
    "min_lon":77.45,
    "max_lon":77.75,
}

def is_in_blr(lat,lon):
    return (lat<=bangalore_bounds["max_lat"] and lat>=bangalore_bounds["min_lat"] and lon<=bangalore_bounds["max_lon"] and lon>=bangalore_bounds["min_lon"])

lat, lon = geocode("Indiranagar, Bangalore")
print(is_in_blr(lat, lon))

lat2, lon2 = geocode("Mumbai")
print(is_in_blr(lat2, lon2))