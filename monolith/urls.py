from django.urls import path
from . import views

urlpatterns = [
    path('get-experiences/', views.get_experiences),
]
