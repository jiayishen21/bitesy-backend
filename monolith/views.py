import google.generativeai as genai
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Experience
from google.cloud import storage
from google.oauth2 import service_account
import requests
import uuid


# Define project information
from vertexai.preview.vision_models import Image
from vertexai.preview.vision_models import ImageQnAModel
import vertexai

# Initialize Vertex AI

vertexai.init(project=settings.PROJECT_ID, location=settings.LOCATION)


image_qna_model = ImageQnAModel.from_pretrained("imagetext@001")

genai.configure(api_key=settings.GEMINI_API_KEY)

# Set up the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
]

model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

convo = model.start_chat(history=[])


@require_http_methods(["GET"])
def get_experiences(request):
    try:
        experiences = Experience.objects.all().order_by('-time')
        # Convert the queryset into a list of dicts
        experiences_list = list(experiences.values(
            'image', 'title', 'calories', 'location', 'time'))  # manual serialization
        # 'safe=False' is needed when passing a list
        return JsonResponse(experiences_list, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def add_experience(request):
    try:
        image_url = request.POST.get('image_url')
        if not image_url:
            return JsonResponse({'error': 'image_url is required'}, status=400)

        # fetch the file from the url
        response = requests.get(image_url)
        if response.status_code != 200:
            return JsonResponse({'error': 'image_url is invalid'}, status=400)

        # prepare file content
        image_content = ContentFile(response.content)

        # Load credentials using google-auth
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS)

        # google cloud client
        client = storage.Client(
            credentials=credentials)
        bucket = client.get_bucket(settings.GS_BUCKET_NAME)

        extension = image_url.split('.')[-1]
        # store the image with filename as uuid
        blob = bucket.blob(f"{uuid.uuid4()}.{extension}")

        blob.upload_from_string(
            image_content.read(),
            content_type=response.headers['Content-Type']
        )

        calories = process_calories(blob.public_url)

        experience = Experience(
            image=blob.public_url,
            calories=calories,
            title=request.POST['title'],
            location=request.POST['location'],
        )
        experience.save()

        # manual serialization
        data = {
            'id': experience.id,
            'image': experience.image,
            'title': experience.title,
            'calories': experience.calories,
            'location': experience.location,
            'time': experience.time.isoformat()
        }

        return JsonResponse({'experience': data, }, status=201)

    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)


def process_calories(url):

    # Load the image file as Image object
    cloud_next_image = Image.load_from_file(url)

    # Ask a question about the image
    res = image_qna_model.ask_question(
        image=cloud_next_image,
        question="Food name and number of servings in the image. Must give the answer in the format 'food name: number of servings' e.g. 'apple: 2'",
        number_of_results=3,
    )
    print(res)

    convo.send_message(
        f"how many calories are in the following food items: {res[0]}. State only the calories with no explanations or any other words.")

    return convo.last.text
