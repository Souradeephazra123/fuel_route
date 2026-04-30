import json
from django.core.management.base import BaseCommand

from routeplanner.models import FuelStation


class Command(BaseCommand):
    help = 'Import fuel price data from a JSON file'

    def handle(self, *args, **kwargs):
        file_path="data/oil_stations_with_prices.json"

        with open(file_path,"r",encoding='utf-8') as file:
            fuel_data=json.load(file)

        for item in fuel_data:
            FuelStation.objects.update_or_create(
                station_id=item["station_id"],
                defaults={
                    "name": item["name"],
                    "city": item["city"],
                    "state": item["state"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "price_per_gallon": item["price_per_gallon"],
                }
            )

        self.stdout.write(self.style.SUCCESS("Fuel price imported sucessfully"))