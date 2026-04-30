import math

def haversine_distance(lat1,lon1,lat2,lon2):
    """
    Calculate the distance in miles between two lat and ling points
    """

    earth_radius_miles = 3958.8

    lat1_rad=math.radians(lat1)
    lon1_rad=math.radians(lon1)
    lat2_rad=math.radians(lat2)
    lon2_rad=math.radians(lon2)

    delta_lat=lat2_rad-lat1_rad
    delta_lon=lon2_rad-lon1_rad

    a=(math.sin(delta_lat/2)** 2 +  math.cos(lat1_rad)*math.cos(lat2_rad) * math.sin(delta_lon/2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return earth_radius_miles * c
