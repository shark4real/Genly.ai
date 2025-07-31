from django.urls import path
from . import views

urlpatterns = [
    path('', views.generate_email, name='home'),  # Change from views.home to views.generate_email
]
