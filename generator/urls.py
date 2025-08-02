from django.urls import path
from . import views

urlpatterns = [
    path('', views.generate_email, name='home'),
    path('send-bulk/', views.send_bulk_email, name='send_bulk'),
]
