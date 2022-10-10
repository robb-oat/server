import json
import os

import openai
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

openai.organization = os.environ['OPENAI_ORG_ID']
openai.api_key = os.environ['OPENAI_API_KEY']

def homepage(request):
    return HttpResponse('Greetings, program! 💃')

@csrf_exempt
def webhook(request):
    data = json.loads(request.body)
    body = data['issue']['body'] or ''  # body can be None
    lines = body.splitlines()
    if not lines:
        return HttpResponseBadRequest('Empty issue')
    filespec = lines[0]
    instruction = ''
    if len(lines) > 2:
        instruction = lines[2:]
    else:
        return HttpResponseBadRequest('What is your instruction?')
    return HttpResponse(f'''
    Greetings, GitHub!<br><br>
    OpenAI Org ID is {openai.organization}<br><br>
    filespec: {filespec}<br><br>
    instruction: {instruction}
    ''')
