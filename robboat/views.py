import json
import re
import os

import httpx
import openai
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from github_bot_api import GithubApp
from github.InputGitTreeElement import InputGitTreeElement

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
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf.settings import OPENAI_API_SECRET
from file.models import Repository
import re
import httpx


@require_POST
@csrf_exempt
def github_webhook(request, org_repo):
    repository = Repository.get_or_error(org_repo)
    if request.META['HTTP_X_GITHUB_EVENT'] != 'issues':
        return JsonResponse({
            'ignored': f'{request.META["HTTP_X_GITHUB_EVENT"]}.{request.META["HTTP_X_GITHUB_EVENT"]}'
        })
    # print(request.body)
    event = json.loads(request.body)
    event_type = request.META['HTTP_X_GITHUB_EVENT']
    event_subtype = request.META.get('HTTP_X_GITHUB_EVENT')
    print(event_type, event_subtype)

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
    all_lines = body.splitlines()
    if len(all_lines) < 3:
        return HttpResponseBadRequest('Too few lines')
    filespec = filespec_re.match(all_lines[0])
    if filespec is None:
        return HttpResponseBadRequest('Malformed filespec')
    sha, filepath, start, end = filespec.groups()
    start, end = map(int, (start, end))
    instruction = '\n'.join(all_lines[2:])

    content_url = f'https://raw.githubusercontent.com/{org_repo}/{sha}/{filepath}'
    content_lines = httpx.get(content_url).text.splitlines()
    before = '\n'.join(content_lines[:start-1])
    old_passage = '\n'.join(content_lines[start-1:end])
    after = '\n'.join(content_lines[end:])
    answer = openai.Edit.create(model='code-davinci-edit-001', input=old_passage, instruction=instruction)
    new_passage = answer['choices'][0]['text']
    new_content = before + new_passage + after

    repo = github_app.installation_client(installation_id).get_repo(org_repo)

    branch = f'issue-{issue_number}'
    old_commit = repo.get_git_commit(sha)
    new_tree = repo.create_git_tree(
        [InputGitTreeElement(filepath, '100644', 'blob', new_content)],
        old_commit.tree,
    )
    new_commit = repo.create_git_commit('robbocommit', new_tree, [old_commit])
    ref = repo.create_git_ref(f'refs/heads/{branch}', new_commit.sha)
    pr = repo.create_pull(
        title=f'Address #{issue_number}',
        body=f"How's this? Closes #{issue_number}",
        base='main',
        head=branch,
    )

    return JsonResponse({
        'filespec': filespec.groups(),
        'instruction': instruction,
    })