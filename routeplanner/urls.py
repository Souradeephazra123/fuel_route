from django.urls import path
from .views import get_route_data,get_all_fuel_stations,candidate_stations,optimize_fuel_plan

urlpatterns = [
    path('get-route/', get_route_data, name='Get Route Data'),
    path('fuel-stations/', get_all_fuel_stations, name='Get All Fuel Stations'),
    path('candidate-stations/', candidate_stations, name='Get Candidate Fuel Stations'),
    path('optimized-fuel-plan/', optimize_fuel_plan, name='Get Optimized Fuel Plan'),
]
