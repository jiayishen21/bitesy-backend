from django.db import models

# Create your models here.


class Experience(models.Model):
    image1 = models.CharField(max_length=120, blank=False)
    image2 = models.CharField(max_length=120, blank=False)
    title = models.CharField(max_length=300, default='')
    calories = models.CharField(max_length=30, default='0')
    location = models.CharField(max_length=200)
    time = models.DateTimeField(auto_now_add=True)
