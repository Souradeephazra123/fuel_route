from routeplanner.models import FuelStation
from routeplanner.utils.distance import haversine_distance
from routeplanner.utils.timing import timeit


@timeit("get_station_near_route")
def get_station_near_route(route_geometry, threshold_miles=10, sample_rate=100):
    """
    Find fuel stations near the route
    route_geometry format example:
    [
        [lng, lat],
        [lng, lat],
        ...
    ]

    threshold_miles:
        A station is considered near the route if it is within this distance
        from at least one sampled route point.

    sample_rate:
        To improve performance, we do not check every route point.
        We check every Nth point.
    """

    all_stations = FuelStation.objects.all()

    candidate_stations = []

    added_station_ids = set()

    sampled_points = route_geometry[::sample_rate]

    if route_geometry and route_geometry[-1] not in sampled_points:
        sampled_points.append(route_geometry[-1])

    for station in all_stations:

        for index, points in enumerate(sampled_points):

            point_lon = points[0]
            point_lat = points[1]

            distance = haversine_distance(
                point_lat, point_lon, station.latitude, station.longitude
            )

            if distance <= threshold_miles:

                if station.station_id not in added_station_ids:
                    candidate_stations.append(station)
                    added_station_ids.add(station.station_id)
                break

    return candidate_stations


@timeit("calculate_cumulative_distances")
def calculate_cumulative_distances(route_geometry):
    """
    For each route point, calculate cumulative distance from the start.
    Returns a list where each item contains:
    {
        "point": [lng, lat],
        "distance_from_start": miles
    }
    """
    if not route_geometry:
        return []

    cumulative_points = []
    total_distance = 0.0

    first_point = route_geometry[0]
    cumulative_points.append({"point": first_point, "distance_from_start": 0.0})

    for i in range(1, len(route_geometry)):
        prev_point = route_geometry[i - 1]
        current_point = route_geometry[i]

        prev_lon, prev_lat = prev_point[0], prev_point[1]
        current_lon, current_lat = current_point[0], current_point[1]

        segment_distance = haversine_distance(
            prev_lat, prev_lon, current_lat, current_lon
        )

        total_distance += segment_distance

        cumulative_points.append(
            {"point": current_point, "distance_from_start": total_distance}
        )

    return cumulative_points


@timeit("attach_distance_from_start")
def attach_distance_from_start(candidate_stations, route_geometry):
    """
    For each station, find the closest route point and assign
    approximate distance from start.
    """
    cumulative_points = calculate_cumulative_distances(route_geometry)

    stations_with_progress = []

    for station in candidate_stations:
        min_distance_to_route = float("inf")
        best_distance_from_start = None

        for item in cumulative_points:
            point = item["point"]
            point_lon = point[0]
            point_lat = point[1]

            distance_to_station = haversine_distance(
                point_lat, point_lon, station.latitude, station.longitude
            )

            if distance_to_station < min_distance_to_route:
                min_distance_to_route = distance_to_station
                best_distance_from_start = item["distance_from_start"]

        stations_with_progress.append(
            {
                "station_id": station.station_id,
                "name": station.name,
                "city": station.city,
                "state": station.state,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "price_per_gallon": station.price_per_gallon,
                "distance_from_start_miles": (
                    round(best_distance_from_start, 2)
                    if best_distance_from_start is not None
                    else None
                ),
            }
        )

    stations_with_progress.sort(key=lambda x: x["distance_from_start_miles"] or 0)

    return stations_with_progress
