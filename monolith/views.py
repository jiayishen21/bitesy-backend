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
            # manual serialization
            'id', 'image1', 'image2', 'title', 'calories', 'location', 'time'))
        # 'safe=False' is needed when passing a list
        return JsonResponse({'experiences': experiences_list}, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_experience(request):
    try:
        # Load credentials using google-auth
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS)

        # google cloud client
        client = storage.Client(
            credentials=credentials)
        bucket = client.get_bucket(settings.GS_BUCKET_NAME)

        file1 = request.FILES['image1']
        extension1 = file1.name.split('.')[-1]
        blob1 = bucket.blob(f"{uuid.uuid4()}.{extension1}")

        blob1.upload_from_file(
            file1,
            content_type=file1.content_type
        )

        file2 = request.FILES['image2']
        extension2 = file2.name.split('.')[-1]
        blob2 = bucket.blob(f"{uuid.uuid4()}.{extension2}")

        blob2.upload_from_file(
            file2,
            content_type=file2.content_type
        )

        calories = process_calories(blob1.public_url)

        experience_title = ''
        if 'title' in request.POST:
            experience_title = request.POST['title']

        if 'location' in request.POST:
            experience_location = request.POST['location']

        experience = Experience(
            image1=blob1.public_url,
            image2=blob2.public_url,
            calories=calories,
            title=experience_title,
            location=experience_location,
        )
        experience.save()

        # manual serialization
        data = {
            'id': experience.id,
            'image1': experience.image1,
            'image2': experience.image2,
            'title': experience.title,
            'calories': experience.calories,
            'location': experience.location,
            'time': experience.time.isoformat()
        }

        return JsonResponse({'experience': data, }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def process_calories(url):

    # Load the image file as Image object
    cloud_next_image = Image.load_from_file(url)

    # Ask a question about the image
    res = image_qna_model.ask_question(
        image=cloud_next_image,
        question="Food name and number of servings",
        number_of_results=3,
    )

    prompt = f"i told vertexai to summarize an image, and it gave a couple of possible outputs. three possible interpretations of the image are: \
    {res[0]}, {res[1]}, {res[2]}. \
    based on the ones that make sense, can you tell me how many calories are in the image? output only a single calorie count, not explanations."

    convo.send_message(prompt)

    return convo.last.text
