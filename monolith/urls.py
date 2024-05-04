from django.urls import path
from . import views

urlpatterns = [
    path('get-experiences/', views.get_experiences),
    path('add-experience/', views.add_experience),
]
