from django.db import models

# Create your models here.


class Experience(models.Model):
    image = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    calories = models.IntegerField()
    location = models.CharField(max_length=100)
    time = models.DateTimeField()
