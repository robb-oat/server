from django.urls import path

from .views import homepage, webhook

urlpatterns = [
    path('', homepage, name='homepage'),
    path('webhook', webhook, name='webhook'),
]
