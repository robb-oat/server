from django.http import HttpResponse

def homepage(request):
    return HttpResponse('Greetings, program!')

def webhook(request):
    return HttpResponse('Greetings, GitHub!')
