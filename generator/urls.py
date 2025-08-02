from django.urls import path
from . import views

urlpatterns = [
    path('', views.generate_email, name='home'),
    path('authorize/', views.authorize_gmail, name='authorize_gmail'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    path('send-bulk/', views.send_bulk_email, name='send_bulk'),
]
