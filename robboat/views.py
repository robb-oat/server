import os

import openai
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

openai.organization = os.environ['OPENAI_ORG_ID']
openai.api_key = os.environ['OPENAI_API_KEY']

def homepage(request):
    return HttpResponse('Greetings, program! 💃')

@csrf_exempt
def webhook(request):
    return HttpResponse(f'Greetings, GitHub!<br><br>OpenAI Org ID is {openai.organization}')
