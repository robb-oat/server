import json
import re
import os

import httpx
import openai
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.template.response import TemplateResponse
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
BOT_USER_ID = int(os.environ['GITHUB_BOT_USER_ID'])

filespec_re = re.compile(r'https://github.com/[^/]+/[^/]+/blob/(?P<sha>[^/]+)/(?P<filepath>[^#]+)#L(?P<start>\d+)(?:-L(?P<end>\d+))?')


def homepage(request):
    return TemplateResponse(request, 'homepage.html')


def privacy(request):
    return TemplateResponse(request, 'privacy.html')


def error(request):
    raise heck


@csrf_exempt
def webhook(request):

    # Parse event
    event = json.loads(request.body)
    event_type = request.headers['X-GitHub-Event']
    event['X-GitHub-Event'] = event_type  # Kludge. Why is this not already in here somewhere?
    event_subtype= event['action']

    # Parse repo
    installation_id = event['installation']['id']
    org_repo = event['repository']['full_name']
    repo = github_app.installation_client(installation_id).get_repo(org_repo)

    # Hand off
    func = globals().get(f'handle_{event_type}_{event_subtype}', ignore)
    return func(repo, event)


def ignore(repo, event, reason='uninteresting event'):
    return JsonResponse({
        'ignored': f"{event['X-GitHub-Event']}.{event['action']}",
        'reason': reason,
    })


def handle_issues_opened(repo, event):
    body = event['issue']['body'] or ''  # body can be None
    issue_number = event['issue']['number']
    all_lines = body.splitlines()
    if len(all_lines) < 3:
        return ignore(repo, event, 'too few lines')
    filespec = filespec_re.match(all_lines[0])
    if filespec is None:
        return ignore(repo, event, 'malformed filespec')
    sha, filepath, start, maybe_end = filespec.groups()
    if maybe_end is None:
        start = int(start)
        end = start+1
    else:
        start, end = map(int, (start, maybe_end))
    instruction = '\n'.join(all_lines[2:])
    branch = f'issue-{issue_number}'

    new_commit, response = edit(repo, branch, sha, filepath, start, end, instruction)

    # Open a new pull request.
    repo.create_git_ref(f'refs/heads/{branch}', new_commit.sha)
    repo.create_pull(
        title=f'Address #{issue_number}',
        body=f"How's this? Closes #{issue_number}",
        base='main',
        head=branch,
    )
    return response

handle_issues_edited = handle_issues_opened


def handle_pull_request_review_comment_created(repo, event):
    if event['pull_request']['user']['id'] != BOT_USER_ID:
        # It would be really no good if we responded to every pull request
        # comment in a busy repo. I shudder at the thought.
        return ignore(repo, event, 'not our PR')

    comment = event['comment']
    if comment['user']['id'] == BOT_USER_ID:
        # Less bad (since GitHub has some protection built-in for this) but
        # still bad if we respond recursively to our own comments.
        return ignore(repo, event, 'avoiding recursion')

    instruction = comment['body']
    filepath = comment['path']
    sha = comment['commit_id'] # github.com/orgs/community/discussions/24449 tho
    maybe_start = comment['start_line']
    end = int(comment['line'])
    start = maybe_start if maybe_start is not None else end
    branch = event['pull_request']['head']['ref']

    new_commit, response = edit(repo, branch, sha, filepath, start, end, instruction)

    # Update the PR and reply in the comments.
    repo.get_git_ref(f'heads/{branch}').edit(new_commit.sha)
    pr = repo.get_pull(event['pull_request']['number'])
    pr.create_review_comment_reply(comment['id'], f'Done in {new_commit.sha}.')

    return response


def edit(repo, branch, sha, filepath, start, end, instruction):
    content_url = f'https://raw.githubusercontent.com/{repo.full_name}/{sha}/{filepath}'
    content_lines = httpx.get(content_url).text.splitlines()
    before = '\n'.join(content_lines[:start-1])
    old_passage = '\n'.join(content_lines[start-1:end])
    after = '\n'.join(content_lines[end:])
    answer = openai.Edit.create(
                model='code-davinci-edit-001',
                input=old_passage,
                instruction=instruction)
    new_passage = answer['choices'][0]['text']
    new_content = before + new_passage + after

    # push
    old_commit = repo.get_git_commit(sha)
    new_tree = repo.create_git_tree(
        [InputGitTreeElement(filepath, '100644', 'blob', new_content)],
        old_commit.tree,
    )
    new_commit = repo.create_git_commit('robbocommit', new_tree, [old_commit])

    response = JsonResponse({
        'sha': sha,
        'filepath': filepath,
        'start': start,
        'end': end,
        'instruction': instruction,
    })
    return new_commit, response
