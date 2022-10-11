import json
import re
import os

import httpx
import openai
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from github_bot_api import GithubApp

openai.organization = os.environ['OPENAI_ORG_ID']
openai.api_key = os.environ['OPENAI_API_KEY']

github_app_private_key = f'''\
-----BEGIN RSA PRIVATE KEY-----
{os.environ['GITHUB_APP_PRIVATE_KEY']}
-----END RSA PRIVATE KEY-----
'''
github_app = GithubApp(
  user_agent='robboat',
  app_id=int(os.environ['GITHUB_APP_ID']),
  private_key=github_app_private_key,
)

filespec_re = re.compile(r'https://github.com/[^/]+/[^/]+/blob/(?P<sha>[^/]+)/(?P<filepath>[^#]+)#L(?P<start>\d+)-L(?P<end>\d+)')
def homepage(request):
    return HttpResponse('Greetings, friend! 😄')

@csrf_exempt
def webhook(request):

    try:    event_type = request.headers['X-GitHub-Event']
    except: return HttpResponseBadRequest('Failed to identify event type')
    try:    event = json.loads(request.body)
    except: return HttpResponseBadRequest('Failed to parse request body as JSON')
    try:    installation_id = event['installation']['id']
    except: return HttpResponseBadRequest('Failed to identify installation')
    try:    org_repo = event['repository']['full_name']
    except: return HttpResponseBadRequest('Failed to identify repository')
    try:    event_subtype= event['action']
    except: return HttpResponseBadRequest('Failed to identify event subtype')

    if (event_type, event_subtype) not in (('issues', 'opened'), ('issues', 'edited')):
        return JsonResponse({
            'ignored': f'{event_type}.{event_subtype}'
        })

    if 'issue' not in event:
        return HttpResponseBadRequest('Malformed POST body - no issue')
    if 'number' not in event['issue']:
        return HttpResponseBadRequest('Malformed POST body - no issue number')
    if 'body' not in event['issue']:
        return HttpResponseBadRequest('Malformed POST body - no issue body')
    body = event['issue']['body'] or ''  # body can be None
    issue_number = event['issue']['number']
    lines = body.splitlines()
    if len(lines) < 3:
        return HttpResponseBadRequest('Too few lines')
    filespec = filespec_re.match(lines[0])
    if filespec is None:
        return HttpResponseBadRequest('Malformed filespec')
    sha, filepath, start, end = filespec.groups()
    start, end = map(int, (start, end))

    code_url = f'https://raw.githubusercontent.com/{org_repo}/{sha}/{filepath}'
    old_code = '\n'.join(httpx.get(code_url).text.splitlines()[start-1:end])
    instruction = '\n'.join(lines)
    answer = openai.Edit.create(model='code-davinci-edit-001', input=old_code, instruction=instruction)
    new_code = answer['choices'][0]['text']

    repo = github_app.installation_client(installation_id).get_repo(org_repo)
    issue = repo.get_issue(issue_number).create_comment(f'''
Okay! 👍

----

{filespec.groups()}

----

{instruction}

----

```python
{old_code}
```

----

```python
{new_code}
```
''')
#    pr = repo.create_pull(
#        title=instructions.splitlines()[0][:50]
#        body='Closes #',
#    )
#
    return JsonResponse({
        'filespec': filespec.groups(),
        'instruction': instruction,
    })