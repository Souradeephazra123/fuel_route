from routeplanner.models import FuelStation
from routeplanner.utils.distance import haversine_distance
from scipy.spatial import cKDTree
import math
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

            
        Newer Optimized Logic with KD-tree:

        Faster near-route station search using KD-tree.

        Logic:
        1. Load all stations
        2. Build KD-tree on station coordinates
        3. Sample route points
        4. For each sampled route point, find all nearby stations within radius
        5. Return unique matched stations
    """

    if not route_geometry:
            return []

    all_stations = list(FuelStation.objects.all())

    if not all_stations:
            return []
        
    station_points = [(station.latitude, station.longitude) for station in all_stations]

    station_tree = cKDTree(station_points)

        # sampled_points=route_geometry[::sample_rate]

        # candidate_stations = []

        # added_station_ids = set()
# 
    sampled_points=route_geometry[::sample_rate]

    if route_geometry and route_geometry[-1] not in sampled_points:
        sampled_points.append(route_geometry[-1])

        #approaximate miles into degrees for KD-tree radius search
        radius_degrees = threshold_miles / 69.0

        matched_station_indices = set()

        for point in sampled_points:
            point_lon, point_lat = point

            nearby_indices = station_tree.query_ball_point([point_lat, point_lon], r=radius_degrees)

            matched_station_indices.update(nearby_indices)

        candidate_stations=[all_stations[i] for i in matched_station_indices]

        # for station in all_stations:
            
        #     for index, points in enumerate(sampled_points):
                
        #         point_lon=points[0]
        #         point_lat=points[1]

        #         distance=haversine_distance(point_lat, point_lon, station.latitude, station.longitude)
               
        #         if distance <= threshold_miles:
                  
        #             if station.station_id not in added_station_ids:
        #                 candidate_stations.append(station)
        #                 added_station_ids.add(station.station_id)
        #             break

          
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
def attach_distance_from_start( candidate_stations, route_geometry,sample_rate=20):
        
        """
        For each station, find the closest route point and assign
        approximate distance from start.(older)

         Faster version:
            1. Sample route geometry
            2. Compute cumulative distance on sampled route
            3. Build KD-tree from sampled route points
            4. For each station, find nearest sampled route point
            5. Use that point's cumulative distance as station progress
        """

        if not route_geometry or not candidate_stations:
             return []
        
        sample_route=route_geometry[::sample_rate]
        if route_geometry and route_geometry[-1] not in sample_route:
            sample_route.append(route_geometry[-1])

        cumulative_distances=[0.0]

        for i in range(1,len(sample_route)):
             prev_lon,prev_lat=sample_route[i-1]
             current_lon,current_lat=sample_route[i]

             segment_distance=haversine_distance(
                  prev_lat,prev_lon,
                  current_lat,current_lon
             )

             cumulative_distances.append(cumulative_distances[-1]+segment_distance)


        route_points_for_tree = [
             [point[1],point[0]] for point in sample_route
        ]

        tree=cKDTree(route_points_for_tree)




        # cumulative_points = calculate_cumulative_distances(route_geometry)

        stations_with_progress = []

        for station in candidate_stations:
            station_point = [station.latitude, station.longitude]

            distance,index = tree.query(station_point)

            distance_from_start_miles = cumulative_distances[index]

            stations_with_progress.append({
            "station_id": station.station_id,
            "name": station.name,
            "city": station.city,
            "state": station.state,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "price_per_gallon": station.price_per_gallon,
            "distance_from_start_miles": round(distance_from_start_miles, 2)
            })
            
            # min_distance_to_route = float("inf")
            # best_distance_from_start = None

            # for item in cumulative_points:
            #     point = item["point"]
            #     point_lon = point[0]
            #     point_lat = point[1]

            #     distance_to_station = haversine_distance(
            #         point_lat,
            #         point_lon,
            #         station.latitude,
            #         station.longitude
            #     )

            #     if distance_to_station < min_distance_to_route:
            #         min_distance_to_route = distance_to_station
            #         best_distance_from_start = item["distance_from_start"]

            # stations_with_progress.append({
            #     "station_id": station.station_id,
            #     "name": station.name,
            #     "city": station.city,
            #     "state": station.state,
            #     "latitude": station.latitude,
            #     "longitude": station.longitude,
            #     "price_per_gallon": station.price_per_gallon,
            #     "distance_from_start_miles": round(best_distance_from_start, 2) if best_distance_from_start is not None else None
            # })

        stations_with_progress.sort(key=lambda x: x["distance_from_start_miles"] or 0)

        return stations_with_progress




def prefilter_candidate_stations(stations_with_progress, bucket_size_miles=50, keep_per_bucket=2):
    buckets = {}

    for station in stations_with_progress:
        bucket = int(station["distance_from_start_miles"] // bucket_size_miles)

        if bucket not in buckets:
            buckets[bucket] = []

        buckets[bucket].append(station)

    filtered = []

    for bucket_stations in buckets.values():
        bucket_stations.sort(key=lambda x: x["price_per_gallon"])
        filtered.extend(bucket_stations[:keep_per_bucket])

    filtered.sort(key=lambda x: x["distance_from_start_miles"])
    return filtered