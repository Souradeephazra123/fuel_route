from rest_framework import serializers
from .models import FuelStation

class RouteInputSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class FuelStationSerializer(serializers.ModelSerializer):
    class Meta:
        model=FuelStation
        fields = '__all__'
    


class OptimizedFuelPlanRequestSerializer(serializers.Serializer):
    start=serializers.CharField()
    end=serializers.CharField()

    max_range_miles=serializers.FloatField(required=False, default=500, min_value=1)

    mpg=serializers.FloatField(required=False, default=10, min_value=1)

    start_fuel_percentage=serializers.FloatField(required=False, default=100, min_value=0, max_value=100)

    fuel_step_miles=serializers.FloatField(required=False, default=10, min_value=1)

    start_price_per_gallon=serializers.FloatField(required=False,allow_null=True, default=None, min_value=0)