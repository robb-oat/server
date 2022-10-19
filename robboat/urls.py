from django.urls import path

from .views import homepage, error, privacy, webhook

urlpatterns = [
    path('', homepage, name='homepage'),
    path('error', error, name='error'),
    path('privacy', privacy, name='privacy'),
    path('webhook', webhook, name='webhook'),
]
