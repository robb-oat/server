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
    try:
        data = json.loads(request.body)
    except:
        return HttpResponseBadRequest('Failed to parse request body as JSON')
    if 'issue' not in data:
        return HttpResponseBadRequest('Malformed POST body - no issue')
    if 'body' not in data['issue']:
        return HttpResponseBadRequest('Malformed POST body - no issue body')
    body = data['issue']['body'] or ''  # body can be None
    lines = body.splitlines()
    if len(lines) < 3:
        return HttpResponseBadRequest('Too few lines')
    filespec = lines.pop()
    lines.pop()
    instruction = '\n'.join(lines)
    return HttpResponse(f'''
    Greetings, GitHub!<br><br>
    OpenAI Org ID is {openai.organization}<br><br>
    filespec: {filespec}<br><br>
    instruction: {instruction}
    ''')
