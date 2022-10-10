from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

def homepage(request):
    return HttpResponse('Greetings, program! 💃')

@csrf_exempt
def webhook(request):
    return HttpResponse('Greetings, GitHub!')
