from django.urls import path

from .views import homepage, webhook, privacy

urlpatterns = [
    path('', homepage, name='homepage'),
    path('privacy', privacy, name='privacy'),
    path('webhook', webhook, name='webhook'),
]
