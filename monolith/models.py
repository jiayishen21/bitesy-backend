from django.db import models

# Create your models here.


class Experience(models.Model):
    image = models.CharField(max_length=120, blank=False)
    title = models.CharField(max_length=300, default='')
    calories = models.IntegerField(default=0)
    location = models.CharField(max_length=200)
    time = models.DateTimeField(auto_now_add=True)
