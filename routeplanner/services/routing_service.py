from django.conf import settings
import requests
from typing import TypedDict,Union
from django.core.cache import cache
import hashlib
import json

Openrouter_Base_Url="https://api.openrouteservice.org"

API_KEY=settings.ORS_API_KEY


class CoordinateData(TypedDict):
    location:str
    longitude:float
    latitude:float

class Error(TypedDict):
    error:str

CoordinateResult = Union[CoordinateData, Error]

class RouteDetailsData(TypedDict):
    distance:float
    duration:float
    geometry: list[list[float]]

RouteDetails = Union[RouteDetailsData, Error]



def get_distance_and_duration_and_route_geometry(start, end) -> RouteDetails:

    print("openrouteservice routing api is called with start:", start, "end:", end)

    raw_key=json.dumps({"start":start,"end":end},sort_keys=True)

    hashed_key=hashlib.md5(raw_key.encode()).hexdigest()

    cache_key=f"route:{hashed_key}"

    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    start_coords=get_coordinates(start)
    if "error" in start_coords:
        return {"error": f"Failed to get coordinates for start location: {start}"}

    end_coords=get_coordinates(end)
    if "error" in end_coords:
        return {"error": f"Failed to get coordinates for end location: {end}"}

    start=f"{start_coords['longitude']},{start_coords['latitude']}"
    end=f"{end_coords['longitude']},{end_coords['latitude']}"
    profile="driving-car"

    url=f"{Openrouter_Base_Url}/v2/directions/{profile}"
    params={
        'api_key':API_KEY,
        'start':start,
        'end':end
    }

    response=requests.get(url,params=params)

    response.raise_for_status()
    if response.status_code == 200:
        data=response.json()

        summary=data['features'][0]["properties"]["summary"]

        distance_m=summary["distance"]
        duration_s=summary["duration"]
        geometry = data['features'][0]["geometry"]["coordinates"]

        distance_mile=distance_m/1609.34
        duration_hr=duration_s/3600

        result:RouteDetailsData = {
            "distance":distance_mile,
            "duration":duration_hr,
            "geometry":geometry
        }

        cache.set(cache_key, result,timeout=24*3600)

        return result
    else:
        print(f"Error {response.status_code} {response.text}")
        return {"error":"Failed to fetch route information"}
    



def get_coordinates(location_name:str) -> CoordinateResult:

    cache_key = f"geocode:{location_name.strip().lower()}"
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result
    

    url=f"{Openrouter_Base_Url}/geocode/search"
    params={
        'api_key':API_KEY,
        'text':location_name,
        'size':1
    }

    try:    
        response=requests.get(url,params=params)

        response.raise_for_status()  

        data=response.json()

        if not data['features']:
            print(f"No results found for {location_name}")
            return {"error":f"No results found for {location_name}"}

        coordinates=data['features'][0]["geometry"]["coordinates"]

        result:CoordinateData = { 
            "location": location_name,
            "longitude": coordinates[0],
            "latitude": coordinates[1]
        }
        cache.set(cache_key, result,timeout=24*3600)

        return result
    
    except Exception as e:
        print(f"Error processing geocoding response: {str(e)}")
        return {"error":"Failed to fetch geocoding information"}
