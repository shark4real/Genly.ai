from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('home/', views.generate_email, name='home'),
    path('authorize/', views.authorize_gmail, name='authorize_gmail'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    path('send-single/', views.send_single_email, name='send_single_email'),
    path('bulk-preview/', views.bulk_preview, name='bulk_preview'),
    path('send-bulk/', views.send_bulk_email, name='send_bulk'),
]
