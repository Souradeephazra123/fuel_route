from django.db import models

# Create your models here.


class FuelStation(models.Model):
    station_id = models.IntegerField(unique=True,primary_key=True)
    name= models.CharField(max_length=255)
    city= models.CharField(max_length=255)
    state=models.CharField(max_length=255)
    latitude=models.FloatField()
    longitude=models.FloatField()
    price_per_gallon=models.FloatField()

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.price_per_gallon}/gallon)"
    

    