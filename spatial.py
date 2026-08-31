import h3
import math 
def to_h3(lat, lon, resolution=8):
    cell=h3.latlng_to_cell(lat, lon, resolution)
    return cell
def haversine_km(lat1,lon1,lat2,lon2):
    R=6371
    #the trig fxns are in radians so we convert the degeree from input to radians
    lat1_rad=math.radians(lat1)
    lon1_rad=math.radians(lon1)
    lat2_rad=math.radians(lat2)
    lon2_rad=math.radians(lon2)

    #delta is the diff between the latitudes and longitudes of the 2 points who's diff we calc
    
    dlat=lat2_rad-lat1_rad
    dlon=lon2_rad-lon1_rad

    #now we calc the haversian distance, using the formula(read up)->
    #   a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
    # "sin squared" becomes math.sin(...) ** 2 in Python.
    # `a` itself doesn't mean anything on its own -- it's an intermediate
    # value the haversine formula uses on its way to a real distance.
    a=math.sin(dlat/2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2) ** 2
    # c = 2 * atan2(√a, √(1−a))
    # atan2 is a variant of arctangent (inverse tangent) built to handle
    # angles correctly across all directions, which is why the formula
    # uses it instead of plain atan.
    c= 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    # c is an angle (in radians) representing the two points' separation
    # as seen from Earth's center. Multiplying by Earth's radius converts
    # that angle into an actual arc length -- the real distance in km.
    distance= R*c
    return distance
if __name__ == "__main__":
    cell=to_h3(12.9732913, 77.6443636)
    print("H3 cell:", cell)



    dist=haversine_km(12.9732913, 77.6443636, 12.9352, 77.6146)
    print("Distance (km):", dist)