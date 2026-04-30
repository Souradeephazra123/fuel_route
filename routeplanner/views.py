from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import RouteInputSerializer,FuelStationSerializer,OptimizedFuelPlanRequestSerializer
from .services.routing_service import get_coordinates, get_distance_and_duration_and_route_geometry
from .services.fuel_optimizer import FuelOptimizer
from .services.fuel_station import get_station_near_route,calculate_cumulative_distances,attach_distance_from_start,prefilter_candidate_stations
from .models import FuelStation
# Create your views here.


@api_view(['POST'])
def get_route_data(request):
    serializer = RouteInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

    start=serializer.validated_data['start']
    end=serializer.validated_data['end']

    try :

        start_coords=get_coordinates(start)
        if "error" in start_coords:
            return Response({"error": f"Failed to get coordinates for start location: {start}"}, status=status.HTTP_400_BAD_REQUEST)
        end_coords=get_coordinates(end)
        if "error" in end_coords:
            return Response({"error": f"Failed to get coordinates for end location: {end}"}, status=status.HTTP_400_BAD_REQUEST)

        routeResult=get_distance_and_duration_and_route_geometry(start,end)

        if "error" in routeResult:
            return Response({"error": "Failed to get route information"}, status=status.HTTP_400_BAD_REQUEST)
        
        distance=routeResult['distance']
        duration=routeResult['duration']
        geometry=routeResult['geometry']

        return Response({
            'start':start,
            'finish':end,
            'start_coordinates':start_coords,
            'end_coordinates':end_coords,
            'distant_miles':distance,
            'duration_hours':duration,
            'route_geometry':geometry,
        },status=status.HTTP_200_OK)
    
    except Exception as e:
        print(f"Error processing route data: {str(e)}")
        return Response({"error": "An error occurred while processing the route data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_all_fuel_stations(request):
    fuel_stations = FuelStation.objects.all()
    serializer = FuelStationSerializer(fuel_stations, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
def candidate_stations(request):
    serializer=RouteInputSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

    start = serializer.validated_data['start']
    end = serializer.validated_data['end']

    try:
        route_data=get_distance_and_duration_and_route_geometry(start,end)
        if "error" in route_data:
            return Response({"error": "Failed to get route information"}, status=status.HTTP_400_BAD_REQUEST)
        
        route_geometry=route_data['geometry']

        stations=get_station_near_route(route_geometry=route_geometry,threshold_miles=10,sample_rate=100)
        
        station_serializer=FuelStationSerializer(stations,many=True)

        response_data = {
            "start": start,
            "finish": end,
            "distance_miles": route_data["distance"],
            "duration_hours": route_data["duration"],
            "candidate_station_count": len(stations),
            "candidate_stations": station_serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error processing candidate stations: {str(e)}")
        return Response({"error": "An error occurred while processing candidate stations"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


@api_view(['POST'])
def optimize_fuel_plan(request):
    serializer=OptimizedFuelPlanRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

    data=serializer.validated_data

    start=data['start']
    end=data['end']

    max_range_miles = data["max_range_miles"]
    mpg = data["mpg"]
    start_fuel_percent = data["start_fuel_percentage"]
    fuel_step_miles = data["fuel_step_miles"]
    start_price_per_gallon = data["start_price_per_gallon"]

    safety_buffer_gallons = data["safety_buffer_gallons"]

    fuel_optimizer=FuelOptimizer()

    try:
        route_data=get_distance_and_duration_and_route_geometry(start,end)

        if "error" in route_data:
            return Response({"error": "Failed to get route information"}, status=status.HTTP_400_BAD_REQUEST)

        route_geometry=route_data['geometry']

        route_distance_miles=route_data['distance']

        if route_distance_miles is None:
            return Response({"error": "Route distance information is missing"}, status=status.HTTP_400_BAD_REQUEST)
        
        candidate_stations=get_station_near_route(route_geometry=route_geometry,threshold_miles=10,sample_rate=100)

        station_with_progress=attach_distance_from_start(candidate_stations,route_geometry)

        station_with_progress=prefilter_candidate_stations(station_with_progress)

        optimized_plan=fuel_optimizer.optimizing_fuel_plan(
            station_with_progress=station_with_progress,
            route_distance_miles=route_distance_miles,
            max_range_miles=max_range_miles,
            mpg=mpg,
            start_fuel_percent=start_fuel_percent,
            fuel_step_miles=fuel_step_miles,
            start_price_per_gallon=start_price_per_gallon,
            safety_buffer_gallons=safety_buffer_gallons,
        )

        total_gallons_consumed=route_distance_miles/mpg
        response_data={
            "route":{
                "start":start,
                "finish":end,
                "distance_miles": round(route_distance_miles,2),
                "duration_hours": round(route_data['duration'],2),
            },
            "vehicle":{
                "max_range_miles": max_range_miles,
                "mpg": mpg,
                "tank_capacity_gallons": optimized_plan["tank_capacity_gallons"],
                "safety_buffer_gallons": safety_buffer_gallons,
                "start_fuel_percent": start_fuel_percent,
            },
            "candidate_station_count": len(station_with_progress),
            "fuel_summary":{
                "total_gallons_consumed": round(total_gallons_consumed,2),
                "total_gallons_purchased": round(optimized_plan["total_gallons_purchased"],2),
                "total_fuel_cost": round(optimized_plan["total_cost"],2),
            },
            "fuel_stops":optimized_plan["fuel_stops"]
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    except ValueError as ve:
        print(f"Value error during fuel optimization: {str(ve)}")
        return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        print(f"Error optimizing fuel plan: {str(e)}")
        return Response({"error": "An error occurred while optimizing the fuel plan"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)