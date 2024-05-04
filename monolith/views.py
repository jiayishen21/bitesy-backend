from django.http import JsonResponse
from .models import Experience


def get_experiences(request):
    experiences = Experience.objects.all()
    # Convert the queryset into a list of dicts
    experiences_list = list(experiences.values(
        'image', 'title', 'calories', 'location', 'time'))  # manual serialization
    # 'safe=False' is needed when passing a list
    return JsonResponse(experiences_list, safe=False)
