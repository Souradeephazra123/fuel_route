from django.conf import settings
import requests
from typing import TypedDict, Union
from routeplanner.utils.timing import timeit

Openrouter_Base_Url = "https://api.openrouteservice.org"

API_KEY = settings.ORS_API_KEY


class CoordinateData(TypedDict):
    location: str
    longitude: float
    latitude: float


class Error(TypedDict):
    error: str


CoordinateResult = Union[CoordinateData, Error]


class RouteDetailsData(TypedDict):
    distance: float
    duration: float
    geometry: list[list[float]]


RouteDetails = Union[RouteDetailsData, Error]


@timeit("get_distance_and_duration_and_route_geometry")
def get_distance_and_duration_and_route_geometry(start, end) -> RouteDetails:

    print("openrouteservice routing api is called with start:", start, "end:", end)

    start_coords = get_coordinates(start)
    if "error" in start_coords:
        return {"error": f"Failed to get coordinates for start location: {start}"}

    end_coords = get_coordinates(end)
    if "error" in end_coords:
        return {"error": f"Failed to get coordinates for end location: {end}"}

    start = f"{start_coords['longitude']},{start_coords['latitude']}"
    end = f"{end_coords['longitude']},{end_coords['latitude']}"
    profile = "driving-car"

    url = f"{Openrouter_Base_Url}/v2/directions/{profile}"
    params = {"api_key": API_KEY, "start": start, "end": end}

    response = requests.get(url, params=params)

    response.raise_for_status()
    if response.status_code == 200:
        data = response.json()

        summary = data["features"][0]["properties"]["summary"]

        distance_m = summary["distance"]
        duration_s = summary["duration"]
        geometry = data["features"][0]["geometry"]["coordinates"]

        distance_mile = distance_m / 1609.34
        duration_hr = duration_s / 3600

        return {
            "distance": distance_mile,
            "duration": duration_hr,
            "geometry": geometry,
        }
    else:
        print(f"Error {response.status_code} {response.text}")
        return {"error": "Failed to fetch route information"}


@timeit("get_coordinates")
def get_coordinates(location_name: str) -> CoordinateResult:

    url = f"{Openrouter_Base_Url}/geocode/search"
    params = {"api_key": API_KEY, "text": location_name, "size": 1}

    try:
        response = requests.get(url, params=params)

        response.raise_for_status()

        data = response.json()

        if not data["features"]:
            print(f"No results found for {location_name}")
            return {"error": f"No results found for {location_name}"}

        coordinates = data["features"][0]["geometry"]["coordinates"]

        return {
            "location": location_name,
            "longitude": coordinates[0],
            "latitude": coordinates[1],
        }

    except Exception as e:
        print(f"Error processing geocoding response: {str(e)}")
        return {"error": "Failed to fetch geocoding information"}
